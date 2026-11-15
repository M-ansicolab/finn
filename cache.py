"""Content-addressed cache: every LLM call is keyed on (task, model, input hash).

A filing or transcript is only ever processed once, no matter how many
users or refreshes ask for it. This is the main cost lever.
"""
import hashlib
import json
import os

from config import CACHE_DIR


def _path(task: str, key: str) -> str:
    os.makedirs(os.path.join(CACHE_DIR, task), exist_ok=True)
    return os.path.join(CACHE_DIR, task, key + ".json")


def key_for(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
    return h.hexdigest()[:24]


def get(task: str, key: str):
    p = _path(task, key)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def put(task: str, key: str, value):
    with open(_path(task, key), "w") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
    return value
