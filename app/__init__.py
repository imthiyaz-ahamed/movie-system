from __future__ import annotations

import os
from datetime import datetime
from functools import wraps

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, session, url_for
from pymongo import MongoClient


load_dotenv()


def get_database(app: Flask):
    return app.extensions["mongo_db"]


def close_database(_error=None):
    return None


def init_indexes(app: Flask):
    db = get_database(app)
    db.users.create_index("email", unique=True)
    db.users.create_index("username", unique=True)
    db.movies.create_index("title")
    db.movies.create_index("genres")
    db.ratings.create_index([("user_id", 1), ("movie_id", 1)], unique=True)


def mongo_id(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    return ObjectId(value)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def create_app() -> Flask:
    app = Flask(__name__)
    upload_dir = os.path.join(app.root_path, "static", "uploads", "profiles")
    os.makedirs(upload_dir, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
        MONGO_DB_NAME=os.getenv("MONGO_DB_NAME", "movie_recommendation_db"),
        PROFILE_UPLOAD_DIR=upload_dir,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )
    mongo_client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=3000,
    )
    app.extensions["mongo_client"] = mongo_client
    app.extensions["mongo_db"] = mongo_client[app.config["MONGO_DB_NAME"]]

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
            return
        db = get_database(app)
        g.user = db.users.find_one({"_id": mongo_id(user_id)})

    @app.context_processor
    def inject_globals():
        return {
            "current_user": g.get("user"),
            "current_year": datetime.utcnow().year,
        }

    from .routes import register_routes

    register_routes(app)

    try:
        init_indexes(app)
    except Exception as exc:
        app.logger.warning("MongoDB index initialization failed: %s", exc)

    @app.errorhandler(404)
    def not_found(_error):
        return render_page(
            "Page not found",
            "The page you requested does not exist.",
            404,
        )

    @app.errorhandler(500)
    def server_error(_error):
        return render_page(
            "Server error",
            "Something went wrong while processing your request.",
            500,
        )

    return app


def render_page(title: str, message: str, status: int):
    from flask import render_template

    return render_template("message.html", title=title, message=message), status
