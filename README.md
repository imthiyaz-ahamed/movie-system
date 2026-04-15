# Personalized Movie Recommendation System

This project is a final-year AI/ML web application that recommends movies based on user interests and rating history.

## Tech Stack

- Frontend: HTML, CSS, Jinja templates
- Backend: Python Flask
- Database: MongoDB
- Machine Learning: scikit-learn TF-IDF based content filtering

## Core Features

- User registration and login
- Search movies by title
- Filter movies by genre
- Rate movies on a 1-5 scale
- Automatic recommendations based on watched/rated history
- MongoDB storage for users, movies, and ratings

## Project Structure

```text
final-project/
|-- app/
|   |-- static/
|   |-- templates/
|   |-- __init__.py
|   |-- recommender.py
|   `-- routes.py
|-- data/
|   `-- movies.json
|-- app.py
|-- requirements.txt
|-- seed_movies.py
`-- README.md
```

## How Recommendations Work

1. Each movie is converted into a text profile using its title, genres, cast, director, and description.
2. `TfidfVectorizer` from scikit-learn transforms those text profiles into numerical vectors.
3. The user profile is built from previously rated movies, weighted more heavily for higher ratings.
4. Cosine similarity compares the user profile with unseen movies.
5. The system returns the highest-scoring movies as personalized recommendations.

## Setup Instructions

1. Install the dependencies:

```powershell
python -m pip install --user -r requirements.txt
```

2. Make sure MongoDB is running locally on:

```text
mongodb://localhost:27017/
```

3. Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

4. Seed sample movie data:

```powershell
python seed_movies.py
```

5. Run the application:

```powershell
python app.py
```

6. Open this URL in your browser:

```text
http://127.0.0.1:5000
```

## MongoDB Collections

- `users`: stores login credentials and profile details
- `movies`: stores movie metadata
- `ratings`: stores each user's movie ratings

## Suggested Academic Modules

- Authentication module
- Movie search and filter module
- Recommendation engine module
- User history analysis module
- MongoDB data management module

## Future Enhancements

- Collaborative filtering with user-user similarity
- Admin panel for movie management
- Poster image upload
- Watchlist and favorites
- Hybrid recommendation model
