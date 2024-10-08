import os
import random
from threading import Thread
import time
import json
from uuid import uuid4
from flask import Flask, abort, make_response, request, send_from_directory
import imgkit
import requests
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin
from bson.binary import Binary
from pymongo import MongoClient

load_dotenv()

THEMES = [
    "modern",
    "clean",
    "zen",
    "retro",
    "playful",
    "grand",
]
COMPONENTS = [
    # "checkbox",
    "circular button",
    "button",
    "div",
    # "progress bar",
    # "slider",
    "switch",
]

# access your database and collection from Atlas
# database = mongo_client.get_database(“anaiyamovies”)
# collection = database.get_collection(“movies”)

app = Flask(__name__)
cors = CORS(app)
BREADBOARD_URL = "https://breadboard-community.wl.r.appspot.com/boards/@ArtisticJellyfish/cascade-generator.bgl.api/run"
GRADING_URL = "https://8949-146-152-233-45.ngrok-free.app/"


def render_html(html: str):
    return imgkit.from_string(
        html,
        False,
        options={
            "crop-h": "400",
            "crop-w": "400",
            "--height": "400",
            "--width": "400",
        },
    )


def init_mongo_client(app: Flask):
    try:
        mongo_client = MongoClient(os.getenv("MONGO-CONNECTION-STRING"))

        result = mongo_client.admin.command("ping")

        if int(result.get("ok")) == 1:
            print("Connected")
        else:
            raise Exception("Cluster ping returned OK != 1")
        app.mongo_client = mongo_client
        app.db = mongo_client.bigdata
    except Exception as e:
        print(e)


init_mongo_client(app)


@app.route("/", methods=["GET"])
def index():
    return "this is the cascade backend lesgooooooooo"


@app.route("/start_session", methods=["POST"])
def start_session():
    session_id = uuid4()
    app.db.sessions.insert_one(
        {
            "_id": str(session_id),
            "num_puzzles": 0,
            "current_puzzle": 0,
            "current_puzzle_attempts": 0,
            "skipped_puzzles": [],
            "score": 0,
        }
    )
    res = make_response(str(session_id))
    res.set_cookie("session_id", str(session_id))
    generate_puzzle(str(session_id))
    thread = Thread(target=generate_puzzle, args=[str(session_id)])
    thread.start()
    return res


@app.route("/<session_id>/target/<int:puzzle_num>")
def serve_image(session_id, puzzle_num):
    if not session_id:
        abort(403)
    # puzzle_num = app.db.sessions.find_one({"_id": session_id})[
    #     "current_puzzle"
    # ]
    file = app.db.puzzles.find_one({"_id": f"{session_id}.{puzzle_num}"})
    response = make_response(file["file"])
    response.headers.set("Content-Type", "image/png")
    return response


@app.route("/<session_id>/target/<int:puzzle_num>/points")
def get_puzzle_points(session_id, puzzle_num):
    puzzle = app.db.puzzles.find_one({"_id": f"{session_id}.{puzzle_num}"})
    return str(puzzle["points"])


@app.route("/<session_id>/skip", methods=["POST"])
def skip_puzzle(session_id):
    puzzle_num = app.db.sessions.find_one({"_id": session_id})[
        "current_puzzle"
    ]
    app.db.sessions.update_one(
        {"_id": session_id},
        {
            "$push": {"skipped_puzzles": puzzle_num},
            "$inc": {"current_puzzle": 1},
        },
    )
    thread = Thread(target=generate_puzzle, args=[session_id])
    thread.start()
    print(f"{puzzle_num + 1 = }")
    return str(puzzle_num + 1)


@app.route("/<session_id>/skipped")
def get_skipped(session_id):
    skipped_numbers = app.db.sessions.find_one({"_id": session_id})[
        "skipped_puzzles"
    ]

    res = [f"{session_id}.{num}" for num in skipped_numbers]
    return res


@app.route("/image/<name>")
def get_image(name):
    file = app.db.puzzles.find_one({"_id": name})
    response = make_response(file["file"])
    response.headers.set("Content-Type", "image/png")
    return response


@app.route("/solution/<name>")
def get_solution(name):
    solution = app.db.puzzles.find_one({"_id": name})["solution"]
    return solution


@app.route("/<session_id>/score")
def get_score(session_id):
    session = app.db.sessions.find_one({"_id": session_id})
    return str(session["score"])


@app.route("/<session_id>/submit", methods=["POST"])
def handle_submit(session_id):
    if not session_id:
        abort(403)
    session = app.db.sessions.find_one({"_id": session_id})
    score = session["score"]
    puzzle_num = session["current_puzzle"]

    data = request.get_json()
    html = data["html"]
    attempt_image = render_html(html)
    # attempt_name = f"{session_id}.{puzzle_num}.{attempt_num}"
    # app.db.puzzles.insert_one({"_id": attempt_name, "file": attempt_image})
    puzzle = app.db.puzzles.find_one({"_id": f"{session_id}.{puzzle_num}"})
    target_file = puzzle["file"]

    grading_res = requests.post(
        f"{GRADING_URL}/predict",
        files={
            "image1": ("target", target_file),
            "image2": ("attempt", attempt_image),
        },
    )

    print(f"{grading_res = }")
    print(f"{grading_res.text = }")
    grading_json = grading_res.json()
    sim_score = grading_json["similarity_score"]

    if sim_score > 0.7:  # correct
        puzzle_points = puzzle["points"]
        app.db.sessions.update_one(
            {"_id": session_id},
            {"$inc": {"current_puzzle": 1, "score": puzzle_points}},
        )

        thread = Thread(target=generate_puzzle, args=[session_id])
        thread.start()
        return {"status": "ok", "score": score + puzzle_points}

    app.db.sessions.update_one(
        {"_id": session_id}, {"$inc": {"current_puzzle_attempts": 1}}
    )
    return {"status": "error", "score": score}


# @app.route("/generate", methods=["GET"])
def generate_puzzle(session_id, theme=None, component=None):
    if not theme:
        theme = random.choice(THEMES)
    if not component:
        component = random.choice(COMPONENTS)

    context = f"Theme: {theme}, Component: {component}"
    print(f"{context = }")

    res = requests.post(
        BREADBOARD_URL,
        json={"$key": os.getenv("BREADBOARD-KEY"), "context": context},
    )
    print(f"{res.text = }")
    json_res = res.text[5:]
    data = json.loads(json_res)
    raw_output = data[1]["outputs"]["context"][-1]["parts"][0]["text"]
    raw_output_as_json = raw_output.strip("`json ")
    code_json = json.loads(raw_output_as_json)
    cleaned_html = code_json["html"].replace("\n", "")
    cleaned_css = code_json["css"].replace("\n", "")
    print(f"\n\n{cleaned_html = }")
    print(f"{cleaned_css = }\n\n")

    session = app.db.sessions.find_one({"_id": session_id})
    puzzle_num = session["num_puzzles"]

    combined_html = f"<style>{code_json['css']}</style>{code_json['html']}"
    image = render_html(combined_html)
    image_name = f"{session_id}.{puzzle_num}"

    app.db.puzzles.insert_one(
        {
            "_id": image_name,
            "file": image,
            "solution": combined_html,
            "points": len(combined_html) // 20,
        }
    )
    app.db.sessions.update_one(
        {"_id": session_id}, {"$inc": {"num_puzzles": 1}}
    )
    return image_name


@app.route("/foo")
def foo():
    files = [
        "brown big over.png",
        "small green blue.png",
        "apple apple one.png",
    ]
    for file in files:
        handle = open(file, "rb")
        app.db.puzzles.insert_one(
            {"_id": file, "file": handle, "solution": "foobar", "points": 20}
        )
