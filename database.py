"""
database.py - Centralized MongoDB connection module.
All routes import get_db() from here to avoid __main__ vs app module identity issues.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.uri_parser import parse_uri
import os

_mongo_client = None
_db = None


def get_db():
    """
    Return a live MongoDB database instance.
    Uses lazy initialization with a 3-second timeout.
    Returns None if MongoDB is not reachable.
    """
    global _mongo_client, _db
    if _db is not None:
        return _db

    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/hair_beard_ai')

    try:
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        # Force connection check
        _mongo_client.admin.command('ping')

        # Reliably extract database name from URI
        parsed = parse_uri(mongo_uri)
        db_name = parsed.get('database') or 'hair_beard_ai'

        _db = _mongo_client[db_name]
        print(f"[DB] Connected to MongoDB → database: '{db_name}'")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"[DB] MongoDB not reachable: {e}")
        _db = None
    except Exception as e:
        print(f"[DB] Unexpected error connecting to MongoDB: {e}")
        _db = None

    return _db


def reset_db():
    """Reset connection (used for reconnection attempts)."""
    global _mongo_client, _db
    if _mongo_client:
        try:
            _mongo_client.close()
        except Exception:
            pass
    _mongo_client = None
    _db = None
