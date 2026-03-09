from database import load_json,save_json
from config import MOVIES_FILE
import random

def load_movies():
    return load_json(MOVIES_FILE,{})

def save_movies(data):
    save_json(MOVIES_FILE,data)

def add_movie(code,file,name,quality,duration,caption,movies):

    movies[code]={
        "file":file,
        "name":name,
        "quality":quality,
        "duration":duration,
        "caption":caption,
        "views":0
    }

    save_movies(movies)

def delete_movie(code,movies):

    if code in movies:
        del movies[code]
        save_movies(movies)
        return True

    return False

def random_movie(movies):

    if not movies:
        return None

    return random.choice(list(movies.keys()))

def trending(movies):

    return sorted(
        movies.items(),
        key=lambda x:x[1]["views"],
        reverse=True
    )[:10]
