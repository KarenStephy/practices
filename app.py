import os
import base64
import time
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from flask import Flask, request, jsonify

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from algorithms import ALGORITHMS, make_random_list
from models import Analysis, SessionLocal, init_db

app = Flask(__name__)

# just for school project, normally this secret would not be sitting in the code
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-later"
jwt = JWTManager(app)

# fake "database" of users for now, just a plain dict
# username -> password
USERS = {
    "student": "password123",
}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

init_db()


# these run whenever flask_jwt_extended would normally send back its own
# 401 message, we swap in our own text instead
@jwt.unauthorized_loader
def missing_token_callback(reason):
    # this fires when there is no Authorization header at all
    return jsonify({"error": "I don't know you"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(reason):
    # this fires when a token was sent but it's broken/fake/tampered with
    return jsonify({"error": "Bye"}), 401


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    # this fires when the token was real but it's too old now
    return jsonify({"error": "Bye"}), 401


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if username not in USERS or USERS[username] != password:
        return jsonify({"error": "invalid username or password"}), 401

    access_token = create_access_token(identity=username)

    response = jsonify({
        "message": "logged in, here's your token",
        "access_token": access_token,
    })

    # putting it in the header too (not just the body), as a proper
    # Bearer token, like the assignment asked for
    response.headers["Authorization"] = f"Bearer {access_token}"

    return response


@app.route("/analyze")
def analyze():
    algo = request.args.get("algo")
    step = request.args.get("step", type=int)
    n_max = request.args.get("n_max", type=int)

    if algo is None or step is None or n_max is None:
        return jsonify({
            "error": "Missing parameter. Required: algo, step, n_max."
        }), 400

    if algo not in ALGORITHMS:
        return jsonify({
            "error": f"Unknown algo '{algo}'. Choose from: {list(ALGORITHMS.keys())}"
        }), 400

    if step <= 0 or n_max <= 0:
        return jsonify({"error": "step and n_max must be positive numbers."}), 400

    algo_function = ALGORITHMS[algo]

    sizes = []
    steps_taken = []

    n = 0
    while n <= n_max:
        arr = make_random_list(n)

        start_time = time.perf_counter()
        algo_function(arr)
        elapsed_seconds = time.perf_counter() - start_time

        sizes.append(n)
        steps_taken.append(elapsed_seconds)

        n += step

    plt.figure(figsize=(8, 5))
    plt.plot(sizes, steps_taken, marker="o")
    plt.title("Algorithm Time Complexity Visualiser")
    plt.xlabel("Input Size")
    plt.ylabel("Running Time (seconds)")
    plt.grid(True)

    filename = f"{algo}_{int(time.time())}.png"
    filepath = os.path.join(STATIC_DIR, filename)
    plt.savefig(filepath)
    plt.close()

    with open(filepath, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    return jsonify({
        "algo": algo,
        "step": step,
        "n_max": n_max,
        "sizes": sizes,
        "steps_taken": steps_taken,
        "image_path": filepath,
        "image_base64": encoded_image,
    })


@app.route("/save_analysis", methods=["POST"])
@jwt_required()
def save_analysis():
    # whoever's token this is, just for my own curiosity / could log it later
    current_user = get_jwt_identity()

    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Request body must be JSON."}), 400

    required_fields = ["algo", "step", "n_max", "sizes", "steps_taken", "image_base64"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing field(s): {missing}"}), 400

    analysis = Analysis(
        algo=data["algo"],
        step=data["step"],
        n_max=data["n_max"],
        sizes_json=json.dumps(data["sizes"]),
        steps_taken_json=json.dumps(data["steps_taken"]),
        image_base64=data["image_base64"],
    )

    session = SessionLocal()
    try:
        session.add(analysis)
        session.commit()
        session.refresh(analysis)
        saved = analysis.to_dict()
    finally:
        session.close()

    return jsonify({
        "message": "Analysis saved successfully.",
        "analysis": saved,
    }), 201


@app.route("/analyses")
def list_analyses():
    session = SessionLocal()
    try:
        rows = session.query(Analysis).order_by(Analysis.id.desc()).all()
        results = [row.to_dict() for row in rows]
    finally:
        session.close()

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)
