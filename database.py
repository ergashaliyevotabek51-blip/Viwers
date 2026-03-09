import json
import os

def load_json(file, default):

    if not os.path.exists(file):
        with open(file,"w") as f:
            json.dump(default,f)

    try:
        with open(file,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(file,data):

    with open(file,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
