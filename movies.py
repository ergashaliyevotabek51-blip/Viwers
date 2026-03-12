import random
from typing import List, Optional, Tuple
from database import get_movies, save_movies

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

def increment_movie_views(movie_code: str):
    movies = get_movies()
    if movie_code in movies:
        movies[movie_code]["views"] = movies[movie_code].get("views", 0) + 1
        save_movies(movies)
