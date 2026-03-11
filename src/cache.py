import os
import json
import hashlib
import time
from src.config import CACHE_DIR, CACHE_TTL_HOURS

def _get_cache_path(key: str) -> str:
    """Convert a cache key to a file path."""
    hashed = hashlib.md5(key.encode()).hexdigest()
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{hashed}.json")


def cache_get(key: str) -> dict | None:
    """
    Retrieve a cached value.
    Returns None if not found or expired.
    """
    path = _get_cache_path(key)

    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            entry = json.load(f)

        # Check expiry
        age_hours = (time.time() - entry["timestamp"]) / 3600
        if age_hours > CACHE_TTL_HOURS:
            os.remove(path)
            return None

        return entry["data"]

    except Exception:
        return None


def cache_set(key: str, data: dict) -> None:
    """Store a value in the cache."""
    path = _get_cache_path(key)
    entry = {
        "timestamp": time.time(),
        "data": data
    }
    try:
        with open(path, "w") as f:
            json.dump(entry, f)
    except Exception:
        pass  # cache failures are silent — never block the pipeline


def cache_key(*parts) -> str:
    """Build a cache key from parts."""
    return ":".join(str(p) for p in parts)