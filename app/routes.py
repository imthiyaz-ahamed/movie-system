from __future__ import annotations

import os
import uuid
from datetime import datetime

from flask import current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

from . import get_database, login_required, mongo_id
from .recommender import generate_recommendations

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def register_routes(app):
    @app.route("/")
    def home():
        db = get_database(app)
        movies = list(db.movies.find().sort("year", -1))
        recent_movies = movies[:6]
        recommendations = []
        history = []

        if g.user:
            user_ratings = list(db.ratings.find({"user_id": g.user["_id"]}))
            history = build_history(db, user_ratings)
            recommendations = generate_recommendations(movies, user_ratings, limit=6)

        return render_template(
            "index.html",
            recent_movies=recent_movies,
            recommendations=recommendations,
            history=history,
        )

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not username or not email or not password:
                flash("All fields are required.", "danger")
                return render_template("register.html")

            db = get_database(app)
            if db.users.find_one({"$or": [{"email": email}, {"username": username}]}):
                flash("User with this email or username already exists.", "danger")
                return render_template("register.html")

            user = {
                "username": username,
                "email": email,
                "password_hash": generate_password_hash(password),
                "created_at": datetime.utcnow(),
            }
            profile_picture = request.files.get("profile_picture")
            if profile_picture and profile_picture.filename:
                image_path = save_profile_picture(profile_picture)
                if image_path is None:
                    flash("Invalid image format. Use png, jpg, jpeg, webp, or gif.", "danger")
                    return render_template("register.html")
                user["profile_image"] = image_path

            result = db.users.insert_one(user)
            session.clear()
            session["user_id"] = str(result.inserted_id)
            flash("Registration successful. Welcome!", "success")
            return redirect(url_for("home"))

        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            db = get_database(app)
            user = db.users.find_one({"email": email})

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html")

            session.clear()
            session["user_id"] = str(user["_id"])
            flash("You are logged in.", "success")
            return redirect(url_for("home"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("home"))

    @app.route("/profile", methods=("GET", "POST"))
    @login_required
    def profile():
        db = get_database(app)
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            update_data = {"updated_at": datetime.utcnow()}

            if username:
                existing = db.users.find_one(
                    {"username": username, "_id": {"$ne": g.user["_id"]}},
                )
                if existing:
                    flash("That username is already taken.", "danger")
                    return redirect(url_for("profile"))
                update_data["username"] = username

            profile_picture = request.files.get("profile_picture")
            if profile_picture and profile_picture.filename:
                image_path = save_profile_picture(profile_picture)
                if image_path is None:
                    flash("Invalid image format. Use png, jpg, jpeg, webp, or gif.", "danger")
                    return redirect(url_for("profile"))
                update_data["profile_image"] = image_path

            db.users.update_one({"_id": g.user["_id"]}, {"$set": update_data})
            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile"))

        return render_template("profile.html")

    @app.route("/movies")
    def movies():
        db = get_database(app)
        search = request.args.get("search", "").strip()
        genre = request.args.get("genre", "").strip()

        query = {}
        if search:
            query["title"] = {"$regex": search, "$options": "i"}
        if genre:
            query["genres"] = genre

        movies_list = list(db.movies.find(query).sort("title", 1))
        genres = sorted(db.movies.distinct("genres"))
        return render_template(
            "movies.html",
            movies=movies_list,
            genres=genres,
            selected_genre=genre,
            search_term=search,
        )

    @app.route("/movie/<movie_id>", methods=("GET", "POST"))
    def movie_detail(movie_id: str):
        db = get_database(app)
        movie = db.movies.find_one({"_id": mongo_id(movie_id)})
        if movie is None:
            return render_template(
                "message.html",
                title="Movie not found",
                message="The requested movie does not exist.",
            ), 404

        if request.method == "POST":
            if g.user is None:
                flash("Please log in to rate movies.", "warning")
                return redirect(url_for("login"))

            score = int(request.form.get("score", "0"))
            if score < 1 or score > 5:
                flash("Please submit a rating between 1 and 5.", "danger")
                return redirect(url_for("movie_detail", movie_id=movie_id))

            db.ratings.update_one(
                {"user_id": g.user["_id"], "movie_id": movie["_id"]},
                {
                    "$set": {
                        "score": score,
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            update_movie_rating_stats(db, movie["_id"])
            flash("Your rating was saved and future recommendations are updated.", "success")
            return redirect(url_for("movie_detail", movie_id=movie_id))

        user_rating = None
        if g.user:
            user_rating = db.ratings.find_one({"user_id": g.user["_id"], "movie_id": movie["_id"]})

        similar_movies = list(
            db.movies.find(
                {
                    "_id": {"$ne": movie["_id"]},
                    "genres": {"$in": movie.get("genres", [])},
                }
            ).limit(4)
        )

        return render_template(
            "movie_detail.html",
            movie=movie,
            user_rating=user_rating,
            similar_movies=similar_movies,
        )


def update_movie_rating_stats(db, movie_id):
    ratings = list(db.ratings.find({"movie_id": movie_id}))
    if not ratings:
        db.movies.update_one(
            {"_id": movie_id},
            {"$set": {"average_rating": 0, "rating_count": 0}},
        )
        return

    average = round(sum(item["score"] for item in ratings) / len(ratings), 2)
    db.movies.update_one(
        {"_id": movie_id},
        {"$set": {"average_rating": average, "rating_count": len(ratings)}},
    )


def build_history(db, user_ratings):
    if not user_ratings:
        return []

    movie_ids = [rating["movie_id"] for rating in user_ratings]
    movies = {movie["_id"]: movie for movie in db.movies.find({"_id": {"$in": movie_ids}})}
    history = []
    for rating in sorted(user_ratings, key=lambda item: item.get("updated_at", datetime.min), reverse=True):
        movie = movies.get(rating["movie_id"])
        if movie is None:
            continue
        history.append({"movie": movie, "score": rating["score"]})
    return history[:6]


def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_profile_picture(file_storage):
    filename = secure_filename(file_storage.filename)
    if not filename or not allowed_image(filename):
        return None

    extension = filename.rsplit(".", 1)[1].lower()
    generated_name = f"{uuid.uuid4().hex}.{extension}"
    upload_dir = current_app.config["PROFILE_UPLOAD_DIR"]
    save_path = os.path.join(upload_dir, generated_name)
    file_storage.save(save_path)
    return f"uploads/profiles/{generated_name}"
