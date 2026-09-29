
# Time Complexity Visualizer

A small Flask server that runs an algorithm across a range of input
sizes, times each run, and returns both the raw timing data and a
chart (as a base64-encoded PNG) showing running time vs. input size.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://localhost:8000`.

## Endpoint

### `GET /analyze`

| Query param | Required | Description |
|---|---|---|
| `algo` | yes | Algorithm name, e.g. `linear_search`. See `/algorithms` for the full list. |
| `step` | no (default `1`) | Step size between input sizes. |
| `n_max` | no (default `100`) | Largest input size to test. `n_min` is always `0`. Accepts thousands separators, e.g. `10,000`. |

**Example**

```
http://localhost:8000/analyze?algo=linear_search&step=10&n_max=10000
```

**Response**

```json
{
  "algo": "linear_search",
  "complexity": "O(n)",
  "n_min": 0,
  "n_max": 10000,
  "step": 10,
  "points": [
    {"n": 0, "time_seconds": 0.0000012},
    {"n": 10, "time_seconds": 0.0000021}
  ],
  "image_snapshot_path": "/path/to/snapshots/linear_search_20260101_120000.png",
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "warnings": []
}
```

`image_snapshot_path` points at a PNG saved under `snapshots/` next
to `app.py`; `image_base64` is the same image encoded for direct use
in a browser (`<img src="data:image/png;base64,...">`) or an API
client.

### `POST /login`

Exchange a username/password for a JWT access token, needed to call
`/save_analysis` (see below). This is a small demo user store
(`DEMO_USERS` in `auth.py`), not a real user database:

| username | password |
|---|---|
| `admin` | `admin123` |
| `ivan` | `password123` |

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

The token comes back both in the JSON body (`access_token`) and in
the response's `Authorization` header. To call a protected endpoint,
send that same value back as a **request** header — not a query
parameter:

```
Authorization: Bearer <token>
```

Tokens expire after 1 hour (`JWT_ACCESS_TOKEN_EXPIRES` in `auth.py`).

### `GET|POST /save_analysis` 🔒 requires a valid JWT

Same parameters as `/analyze` (`algo`, `step`, `n_max`), but instead
of just returning the result, it's persisted as a row in a SQLite
database via SQLAlchemy's ORM (see **Database** below). Requires the
`Authorization: Bearer <token>` header from `/login`:

```bash
curl "http://localhost:8000/save_analysis?algo=bubble_sort&step=100&n_max=1000" \
  -H "Authorization: Bearer <token>"
```

A request with no token, a malformed one, or an expired one gets:

```json
{"error": "I don't know you.", "message": "Bye."}
```
with HTTP status `401`.

Returns the new row's `id`:

```json
{
  "message": "Analysis saved to the database.",
  "id": 1,
  "analysis": {
    "id": 1,
    "algo": "bubble_sort",
    "complexity": "O(n^2)",
    "n_min": 0,
    "n_max": 1000,
    "step": 100,
    "points": [...],
    "image_snapshot_path": "/path/to/snapshots/bubble_sort_....png",
    "created_by": "admin",
    "created_at": "2026-09-27T20:26:24.947875"
  },
  "warnings": []
}
```

Note the `analysis` object here omits `image_base64` to keep the
response small — fetch `GET /analyses/<id>` for the full image.
`created_by` records the identity from the JWT (i.e. who saved it).

### `GET /analyses`

Lists every saved analysis (same shape as above, also without
`image_base64`), newest first.

### `GET /analyses/<id>`

Fetches one saved analysis in full, including its `image_base64`.
404s if the id doesn't exist.

### `DELETE /analyses/<id>`

Deletes one saved analysis. 404s if the id doesn't exist.

### `GET /algorithms`

Lists every supported algorithm with its Big-O complexity and the
safe maximum `n` the server allows for it (see **Safety limits**
below).

## Database

Saved analyses (`/save_analysis`) are stored in a local SQLite
database file, `analysis.db`, created automatically next to `app.py`
the first time the server starts. All database access goes through
**SQLAlchemy's ORM** — `database.py` sets up the engine/session, and
`models.py` defines the `AnalysisResult` table as a plain Python
class. There's no raw SQL anywhere in the app.

To point this at a different database later (Postgres, MySQL, etc.),
just change `DATABASE_URL` in `database.py` — nothing else needs to
change, since all the queries go through the ORM.

`analysis.db` is a generated file (like the PNGs in `snapshots/`), so
it's excluded via `.gitignore` rather than committed to the repo.

If you already had an `analysis.db` from before `created_by` was
added to the schema, delete that file and let the server recreate it
on next startup — SQLAlchemy's `create_all()` only creates tables
that don't exist yet, it won't alter an existing one.

## Authentication

⚠️ `auth.py`'s `JWT_SECRET_KEY` has a hardcoded development default
and `DEMO_USERS` are plaintext in source — both are fine for a local
project like this, but neither belongs in a real deployment. Set
`JWT_SECRET_KEY` as an environment variable and replace `DEMO_USERS`
with a real user table (with hashed passwords) before this goes
anywhere public.

## Supported algorithms

| `algo` value | Complexity |
|---|---|
| `linear_search` | O(n) |
| `binary_search` | O(log n) |
| `bubble_sort` | O(n²) |
| `nested_loops` | O(n²) |
| `merge_sort` | O(n log n) |
| `quick_sort` | O(n log n) average |
| `matrix_multiplication` | O(n³) |
| `fibonacci_recursive` | O(2ⁿ) |
| `stack_push_pop` | O(n) |
| `stack_balanced_parentheses` | O(n) |
| `queue_enqueue_dequeue` | O(n) |
| `queue_bfs_traversal` | O(n) |

That's the 4 required algorithms (linear search, binary search,
bubble sort, nested loops), 4 extra sorting/math algorithms (merge
sort, quick sort, matrix multiplication, naive recursive Fibonacci),
and 4 more built on the custom `Stack`/`Queue` data structures below.

## Stack and Queue data structures

`stack.py` and `queue_ds.py` implement a classic `Stack` (LIFO) and
`Queue` (FIFO) from scratch — `Stack` on top of a Python list,
`Queue` on top of `collections.deque` so both ends stay O(1). (The
queue file is named `queue_ds.py` rather than `queue.py` so it
doesn't shadow Python's standard-library `queue` module.) Both raise
a dedicated `StackEmptyError` / `QueueEmptyError` on `pop`/`dequeue`/
`peek` of an empty structure, rather than a bare `IndexError`.

Each has a full unit test suite covering ordering (LIFO/FIFO),
`peek` (non-destructive), size/`len()` tracking, empty-structure
errors, mixed data types, and a 10,000-item stress test:

```bash
python -m unittest test_stack.py test_queue.py -v
# or, with pytest installed:
pytest test_stack.py test_queue.py -v
```

Four algorithms in `algorithms.py` are built directly on these two
structures, so their time complexity can be graphed through
`/analyze` exactly like any other algorithm here:

- **`stack_push_pop`** — push n items onto a `Stack`, then pop them
  all back off. O(n).
- **`stack_balanced_parentheses`** — build a balanced string of 2n
  parentheses (`"(((...)))"`) and validate it with a `Stack`: push on
  `(`, pop on `)`. The classic textbook use of a stack. O(n).
- **`queue_enqueue_dequeue`** — enqueue n items onto a `Queue`, then
  dequeue them all. O(n).
- **`queue_bfs_traversal`** — breadth-first traversal of a simple
  n-node chain graph, using a `Queue` to hold the BFS frontier. O(n).

Try them, e.g.:

```
http://localhost:8000/analyze?algo=stack_push_pop&step=5000&n_max=100000
http://localhost:8000/analyze?algo=queue_bfs_traversal&step=5000&n_max=100000
```

## Safety limits

Some of these algorithms grow fast enough that an unbounded `n_max`
would make a single request take minutes (or longer). To keep the
server responsive:

- Each algorithm has a **max `n`** in `algorithms.py`'s
  `ALGORITHM_CONFIG` (e.g. 150 for matrix multiplication, 32 for
  recursive Fibonacci). A request asking for more is silently
  clamped, and a note is added to the response's `warnings` list.
- The number of `(n, time)` samples in a single request is capped at
  `MAX_DATA_POINTS` (300) in `app.py`. If `step` would produce more
  than that, `step` is increased automatically and a warning is
  returned.

## Fixes from the original prototype

The original script this was built from had a few bugs that would
have prevented it from running at all, and used an interactive,
GUI-based plotting flow that doesn't work in a server process:

- `matplotlib.use('TkAgg')` was called before `matplotlib` itself was
  imported, and needs a display — not available on a server. Swapped
  for the headless `Agg` backend.
- `range(n_min, n_max, + n_step, n_step)` passed 4 arguments to
  `range()`, which only accepts up to 3.
- `line, ax.plot([], [], 'o-')` is a tuple-unpacking bug (missing
  `=`); it would raise `TypeError`.
- `plt.ion()` / `plt.pause()` / `plt.show()` open an interactive
  window and block — replaced with building the figure once,
  saving it to disk, and base64-encoding it for the JSON response.

## Project structure

```
time_complexity_visualizer/
├── app.py            # Flask server: /analyze, /save_analysis, /analyses, /algorithms
├── algorithms.py      # algorithm implementations + complexity/limit registry
├── auth.py              # JWT setup + POST /login (Flask-JWT-Extended)
├── database.py         # SQLAlchemy engine/session setup (SQLite)
├── models.py            # SQLAlchemy ORM model: AnalysisResult
├── stack.py            # Stack (LIFO) data structure
├── queue_ds.py         # Queue (FIFO) data structure
├── test_stack.py        # Stack unit test suite
├── test_queue.py        # Queue unit test suite
├── requirements.txt
├── README.md
├── analysis.db          # SQLite database (created on first run, gitignored)
└── snapshots/          # PNG snapshots saved here on each /analyze or /save_analysis call
```
