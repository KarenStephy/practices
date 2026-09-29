# Time Complexity Visualizer

A small Flask server that visualizes how the number of steps an algorithm
takes grows as the input size grows.

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/Devislastthought/time_complexity_visualizer.git
cd time_complexity_visualizer
```

**2. Install the dependencies**

```bash
pip install -r requirements.txt
```

> If you see an `externally-managed-environment` error (common on newer
> Ubuntu/Debian systems, including WSL), install with:
> ```bash
> pip install --break-system-packages -r requirements.txt
> ```

## Run

```bash
python app.py
```

The server runs at `http://localhost:8000`.

## Usage

Hit the `/analyze` endpoint with three query parameters:

- `algo` — one of: `linear_search`, `binary_search`, `bubble_sort`, `nested_loops`, `selection_sort`, `stack_push_pop`, `queue_enqueue_dequeue`
- `step` — how much to increase the input size by each time
- `n_max` — the largest input size to test (starts from 0)

Example:

```
http://localhost:8000/analyze?algo=linear_search&step=10&n_max=1000
```

## Response

A JSON object containing:

- `sizes` — list of input sizes tested
- `steps_taken` — number of steps the algorithm took at each size
- `image_base64` — base64-encoded PNG chart of size vs steps
- `image_path` — where the chart was saved locally (inside `static/`)

## Algorithms included

- Linear Search — O(n)
- Binary Search — O(log n)
- Bubble Sort — O(n²)
- Nested Loops — O(n²)
- Selection Sort — O(n²)
- Stack push/pop — O(n)
- Queue enqueue/dequeue — O(n)

## Saving results to the database

Results from `/analyze` can be saved permanently using SQLAlchemy
(a SQLite database file, `analysis.db`, is created automatically —
no raw SQL is written anywhere in this project).

`/save_analysis` is locked behind a login now (see below), you need a
token first or it won't let you save anything.

**List everything saved so far** (this one is not locked):

```
http://localhost:8000/analyses
```

## Auth (login required to save)

`/save_analysis` now needs a JWT token. Without one you get blocked.

**Step 1 — log in to get a token.** There's only one hardcoded user for now
(`USERS` dict at the top of `app.py`):

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "student", "password": "password123"}'
```

The token comes back in the response body AND in the `Authorization`
response header (not stuffed into the URL as a query param).

**Step 2 — send that token back as a Bearer token** in the `Authorization`
header on `/save_analysis`:

```bash
curl -X POST http://localhost:8000/save_analysis \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer PASTE_YOUR_TOKEN_HERE" \
  -d @analyze_result.json
```

**What happens if you skip the token / send a bad one:**

| Situation | Response |
|---|---|
| No `Authorization` header at all | `401` — `"I don't know you"` |
| Token is fake / broken / expired | `401` — `"Bye"` |
| Token is valid | request goes through as normal |
