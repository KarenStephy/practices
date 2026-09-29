"""
Flask server for the time complexity visualizer.

GET /analyze?algo=<name>&step=<int>&n_max=<int>
    Runs <name> on input sizes 0, step, 2*step, ... up to n_max,
    timing each run, plots the results with matplotlib, saves a PNG
    snapshot to disk, and returns the timing data plus a base64
    encoding of that same PNG. Nothing is persisted beyond the PNG
    file — this is a "run it and see" endpoint. Public, no auth.

POST /login
    {"username": ..., "password": ...} -> a JWT access token, used to
    authenticate the endpoint below. See auth.py.

GET|POST /save_analysis?algo=<name>&step=<int>&n_max=<int>
    Same run as /analyze, but the full result (timings, chart, image)
    is saved as a row in a SQLite database (via SQLAlchemy) instead
    of just being returned. Requires a valid JWT: send the token from
    /login as an `Authorization: Bearer <token>` request header. A
    request with no token, or an invalid/expired one, gets a 401.

GET /analyses
    Lists every saved analysis (without the base64 image, to keep the
    payload small).

GET /analyses/<id>
    Fetches one saved analysis in full, including its base64 image.

DELETE /analyses/<id>
    Deletes one saved analysis.

GET /algorithms
    Lists the supported algorithm names, their Big-O complexity, and
    the safe max n for each.

Run with:  python app.py
Then try:  http://localhost:8000/analyze?algo=linear_search&step=10&n_max=10000
"""

import base64
import io
import os
import re
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless backend — there is no display in a server process
import matplotlib.pyplot as plt

from flask import Flask, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from algorithms import ALGORITHM_CONFIG
from auth import auth_bp, init_jwt
from database import SessionLocal, init_db
from models import AnalysisResult

app = Flask(__name__)
init_db()
init_jwt(app)
app.register_blueprint(auth_bp)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Hard ceiling on how many (n, time) samples one request can generate,
# independent of n_max/step, so a request can't accidentally ask for
# thousands of runs.
MAX_DATA_POINTS = 300


def _clean_algo_name(raw: str) -> str:
    """Pull a bare algorithm name out of a possibly messy query
    param, e.g. "['linear_search'" -> "linear_search"."""
    return re.sub(r"[^a-zA-Z_]", "", raw or "").lower()


def _clean_int(raw, default: int) -> int:
    """Parse an int query param that may contain thousands
    separators or stray characters, e.g. "10,000" -> 10000."""
    if raw is None:
        return default
    cleaned = re.sub(r"[^0-9]", "", str(raw))
    return int(cleaned) if cleaned else default


def _run_analysis(algo_raw, step_raw, n_max_raw):
    """Run one algorithm across a range of input sizes and build its
    chart. Shared by /analyze and /save_analysis so both stay in sync.

    Returns (result_dict, None) on success, or (None, (response, status))
    on a validation error, ready to be returned directly from a route.
    """
    warnings = []

    algo_name = _clean_algo_name(algo_raw)
    if algo_name not in ALGORITHM_CONFIG:
        return None, (jsonify({
            "error": f"Unknown or missing algorithm '{algo_name}'.",
            "supported_algorithms": list(ALGORITHM_CONFIG.keys()),
        }), 400)

    config = ALGORITHM_CONFIG[algo_name]
    algorithm = config["func"]

    step = _clean_int(step_raw, 1)
    if step <= 0:
        return None, (jsonify({"error": "'step' must be a positive integer."}), 400)

    n_min = 0
    n_max_requested = _clean_int(n_max_raw, 100)

    n_max = n_max_requested
    if n_max > config["max_n"]:
        n_max = config["max_n"]
        warnings.append(
            f"n_max clamped from {n_max_requested} to {n_max} to keep "
            f"{algo_name} ({config['complexity']}) from running too long."
        )

    projected_points = (n_max - n_min) // step + 1
    if projected_points > MAX_DATA_POINTS:
        step = max(step, (n_max - n_min) // MAX_DATA_POINTS)
        warnings.append(
            f"'step' increased to {step} to cap the run at "
            f"~{MAX_DATA_POINTS} data points."
        )

    input_sizes = list(range(n_min, n_max + 1, step))
    if not input_sizes:
        input_sizes = [n_min]

    times = []
    for n in input_sizes:
        start = time.perf_counter()
        algorithm(n)
        times.append(time.perf_counter() - start)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(input_sizes, times, "o-", color="#2563eb")
    ax.set_xlabel("Input size (n)")
    ax.set_ylabel("Running time (seconds)")
    ax.set_title(f"{algo_name} time complexity — {config['complexity']}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{algo_name}_{timestamp}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(filepath, dpi=150)

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    result = {
        "algo": algo_name,
        "complexity": config["complexity"],
        "n_min": n_min,
        "n_max": n_max,
        "step": step,
        "points": [
            {"n": n, "time_seconds": t} for n, t in zip(input_sizes, times)
        ],
        "image_snapshot_path": filepath,
        "image_base64": image_base64,
        "warnings": warnings,
    }
    return result, None


@app.route("/algorithms", methods=["GET"])
def list_algorithms():
    return jsonify({
        name: {"complexity": cfg["complexity"], "max_n": cfg["max_n"]}
        for name, cfg in ALGORITHM_CONFIG.items()
    })


@app.route("/analyze", methods=["GET"])
def analyze():
    result, error = _run_analysis(
        request.args.get("algo", ""),
        request.args.get("step"),
        request.args.get("n_max"),
    )
    if error:
        return error
    return jsonify(result)


@app.route("/save_analysis", methods=["GET", "POST"])
@jwt_required()
def save_analysis():
    """Run an analysis (same params as /analyze) and persist the full
    result — timings, complexity, and the chart — as a row in the
    database via SQLAlchemy, instead of just returning it.

    Requires a valid JWT: send it as `Authorization: Bearer <token>`.
    Get a token from POST /login first.
    """
    args = request.values  # works for both query string and form/JSON-as-form POSTs
    result, error = _run_analysis(
        args.get("algo", ""),
        args.get("step"),
        args.get("n_max"),
    )
    if error:
        return error

    session = SessionLocal()
    try:
        record = AnalysisResult(
            algo=result["algo"],
            complexity=result["complexity"],
            n_min=result["n_min"],
            n_max=result["n_max"],
            step=result["step"],
            points=result["points"],
            image_base64=result["image_base64"],
            image_snapshot_path=result["image_snapshot_path"],
            created_by=get_jwt_identity(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        saved = record.to_dict(include_image=False)
    finally:
        session.close()

    return jsonify({
        "message": "Analysis saved to the database.",
        "id": saved["id"],
        "analysis": saved,
        "warnings": result["warnings"],
    }), 201


@app.route("/analyses", methods=["GET"])
def list_analyses():
    """List every saved analysis, without the (often large) base64
    image, so the response stays small."""
    session = SessionLocal()
    try:
        records = (
            session.query(AnalysisResult)
            .order_by(AnalysisResult.created_at.desc())
            .all()
        )
        return jsonify([r.to_dict(include_image=False) for r in records])
    finally:
        session.close()


@app.route("/analyses/<int:analysis_id>", methods=["GET"])
def get_analysis(analysis_id):
    """Fetch one saved analysis in full, including its base64 image."""
    session = SessionLocal()
    try:
        record = session.get(AnalysisResult, analysis_id)
        if record is None:
            return jsonify({"error": f"No analysis found with id {analysis_id}."}), 404
        return jsonify(record.to_dict(include_image=True))
    finally:
        session.close()


@app.route("/analyses/<int:analysis_id>", methods=["DELETE"])
def delete_analysis(analysis_id):
    session = SessionLocal()
    try:
        record = session.get(AnalysisResult, analysis_id)
        if record is None:
            return jsonify({"error": f"No analysis found with id {analysis_id}."}), 404
        session.delete(record)
        session.commit()
        return jsonify({"message": f"Analysis {analysis_id} deleted."})
    finally:
        session.close()


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "Time complexity visualizer. GET /algorithms for the "
                    "supported list, GET /analyze to run one, or "
                    "GET /save_analysis to run and persist one.",
        "example": "/analyze?algo=linear_search&step=10&n_max=10000",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

