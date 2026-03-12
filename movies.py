import random
from typing import List, Optional, Tuple
from database import get_movies, save_movies
from datetime import datetime

def get_random_movie() -> Optional[Tuple[str, dict]]:
    movies = get_movies()
    if not movies:
        return None
    return random.choice(list(movies.items()))

def get_trending_movies(limit: int = 10) -> List[Tuple[str, dict]]:
    movies = get_movies()
    sorted_movies = sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)
    return sorted_movies[:limit]

def search_movies(query: str) -> List[Tuple[str, dict]]:
    movies = get_movies()
    results = []
    query_lower = query.lower()
    for code, data in movies.items():
        if query_lower in code.lower() or query_lower in data.get("name", "").lower():
            results.append((code, data))
    return results

def get_movies_by_genre(genre: str) -> List[Tuple[str, dict]]:
    movies = get_movies()
    return [(c, d) for c, d in movies.items() if d.get("genre") == genre]

def increment_movie_views(movie_code: str):
    movies = get_movies()
    if movie_code in movies:
        movies[movie_code]["views"] = movies[movie_code].get("views", 0) + 1
        save_movies(movies)

def add_movie(code: str, name: str, genre: str, channel_id: int, message_id: int, added_by: str):
    movies = get_movies()
    movies[code] = {
        "code": code,
        "name": name,
        "genre": genre,
        "channel_id": channel_id,
        "message_id": message_id,
        "views": 0,
        "added_at": datetime.now().isoformat(),
        "added_by": added_by
    }
    save_movies(movies)

def delete_movie(code: str) -> bool:
    movies = get_movies()
    if code in movies:
        del movies[code]
        save_movies(movies)
        return True
    return False
