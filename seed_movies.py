from __future__ import annotations

import json
from pathlib import Path

from pymongo import MongoClient


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "movies.json"


def main():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["movie_recommendation_db"]
    movies = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if db.movies.count_documents({}) > 0:
        print("Movies collection already contains data. Skipping seed.")
        return

    db.movies.insert_many(movies)
    print(f"Inserted {len(movies)} movies.")


if __name__ == "__main__":
    main()
