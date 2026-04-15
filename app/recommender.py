from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def movie_to_text(movie: dict) -> str:
    genres = " ".join(movie.get("genres", []))
    cast = " ".join(movie.get("cast", []))
    description = movie.get("description", "")
    director = movie.get("director", "")
    return f"{movie.get('title', '')} {genres} {cast} {director} {description}".strip()


def generate_recommendations(movies: list[dict], user_ratings: list[dict], limit: int = 8) -> list[dict]:
    if not movies:
        return []

    movie_ids = [str(movie["_id"]) for movie in movies]
    docs = [movie_to_text(movie) for movie in movies]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(docs)

    ratings_by_movie = {str(item["movie_id"]): item["score"] for item in user_ratings}
    watched_movie_ids = set(ratings_by_movie.keys())

    if not watched_movie_ids:
        return top_popular_movies(movies, user_ratings, limit=limit)

    weighted_vectors = []
    weights = []
    for idx, movie_id in enumerate(movie_ids):
        if movie_id in ratings_by_movie:
            score = ratings_by_movie[movie_id]
            weight = max(score - 2.0, 0.1)
            weighted_vectors.append(tfidf_matrix[idx].toarray()[0] * weight)
            weights.append(weight)

    if not weighted_vectors:
        return top_popular_movies(movies, user_ratings, limit=limit)

    user_profile = np.average(np.array(weighted_vectors), axis=0, weights=np.array(weights))
    scores = cosine_similarity([user_profile], tfidf_matrix)[0]

    recommended = []
    for idx, movie in enumerate(movies):
        movie_id = str(movie["_id"])
        if movie_id in watched_movie_ids:
            continue
        movie_copy = dict(movie)
        movie_copy["score"] = round(float(scores[idx]), 4)
        recommended.append(movie_copy)

    recommended.sort(
        key=lambda item: (
            item.get("score", 0),
            item.get("average_rating", 0),
            item.get("rating_count", 0),
        ),
        reverse=True,
    )
    return recommended[:limit]


def top_popular_movies(movies: list[dict], user_ratings: list[dict], limit: int = 8) -> list[dict]:
    aggregate = defaultdict(list)
    for rating in user_ratings:
        aggregate[str(rating["movie_id"])].append(rating["score"])

    enriched = []
    for movie in movies:
        movie_copy = dict(movie)
        scores = aggregate.get(str(movie["_id"]), [])
        movie_copy["score"] = movie_copy.get("average_rating", 0)
        if scores:
            movie_copy["score"] = sum(scores) / len(scores)
        enriched.append(movie_copy)

    enriched.sort(
        key=lambda item: (
            item.get("average_rating", 0),
            item.get("rating_count", 0),
            item.get("year", 0),
        ),
        reverse=True,
    )
    return enriched[:limit]
