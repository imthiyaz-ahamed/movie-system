from __future__ import annotations

import argparse
import csv
import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from pymongo import MongoClient


KNOWN_GENRES = [
    "Science Fiction",
    "TV Movie",
    "Documentary",
    "Animation",
    "Adventure",
    "Fantasy",
    "Thriller",
    "Romance",
    "Western",
    "Mystery",
    "History",
    "Family",
    "Action",
    "Comedy",
    "Drama",
    "Crime",
    "Music",
    "War",
    "Horror",
]


def parse_year(date_text: str) -> int | None:
    date_text = (date_text or "").strip()
    if not date_text:
        return None
    try:
        return int(date_text[:4])
    except ValueError:
        return None


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_genres(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return ["Unknown"]

    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]

    normalized = " ".join(text.split())
    lowered = normalized.lower()
    found = []
    for genre in KNOWN_GENRES:
        if genre.lower() in lowered:
            found.append(genre)

    if found:
        return found

    return [normalized]


def parse_cast(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    if "|" in text:
        return [item.strip() for item in text.split("|") if item.strip()]
    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]
    return [text]


def row_to_movie(row: dict) -> dict | None:
    title = (row.get("title") or row.get("original_title") or "").strip()
    if not title:
        return None

    tmdb_id = parse_int(row.get("id"), default=0)
    if tmdb_id <= 0:
        return None

    release_year = parse_year(row.get("release_date")) or 0
    vote_average = parse_float(row.get("vote_average"), default=0.0)
    vote_count = parse_int(row.get("vote_count"), default=0)

    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "year": release_year,
        "genres": parse_genres(row.get("genres", "")),
        "director": (row.get("director") or "Unknown").strip() or "Unknown",
        "cast": parse_cast(row.get("cast", "")),
        "description": (row.get("overview") or "No description available.").strip(),
        "average_rating": round(vote_average / 2, 2),
        "rating_count": vote_count,
        "popularity": parse_float(row.get("popularity"), default=0.0),
        "updated_at": datetime.now(UTC),
    }


def run_import(csv_path: str, mongo_uri: str, db_name: str) -> tuple[int, int, int]:
    client = MongoClient(mongo_uri)
    db = client[db_name]

    db.movies.create_index("tmdb_id", unique=True, sparse=True)
    db.movies.create_index("title")
    db.movies.create_index("genres")

    inserted = 0
    updated = 0
    skipped = 0

    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            movie = row_to_movie(row)
            if movie is None:
                skipped += 1
                continue

            result = db.movies.update_one(
                {"tmdb_id": movie["tmdb_id"]},
                {"$set": movie},
                upsert=True,
            )
            if result.upserted_id is not None:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1

    return inserted, updated, skipped


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Import movies from CSV into MongoDB.")
    parser.add_argument("--csv", required=True, help="Absolute path to movies.csv")
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    )
    parser.add_argument(
        "--db-name",
        default=os.getenv("MONGO_DB_NAME", "movie_recommendation_db"),
    )
    args = parser.parse_args()

    inserted, updated, skipped = run_import(args.csv, args.mongo_uri, args.db_name)
    print(f"Import complete. Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
