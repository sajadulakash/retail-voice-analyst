"""
In-memory store for analysis results and questions.
Questions are persisted to a JSON file so they survive server restarts.
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

_lock = threading.Lock()
_store: Dict[str, dict] = {}

# --- Questions store ---
_questions_lock = threading.Lock()
_questions: Dict[str, dict] = {}

# Path to the persistent questions file  (backend/data/questions.json)
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_QUESTIONS_FILE = os.path.join(_DATA_DIR, "questions.json")


def _load_questions_from_disk() -> Optional[List[dict]]:
    """Read questions from the JSON file. Returns None if the file doesn't exist."""
    if not os.path.exists(_QUESTIONS_FILE):
        return None
    try:
        with open(_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[store] Could not read questions file: {e}")
        return None


def _persist_questions() -> None:
    """Write the current questions dict to disk (must be called while holding _questions_lock)."""
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(_questions.values()), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[store] Could not save questions file: {e}")


def init_questions(defaults: List[dict]) -> None:
    """
    Called on startup.
    - If a saved questions.json exists, load it (preserving user edits).
    - Otherwise seed from the provided defaults and save them.
    """
    with _questions_lock:
        saved = _load_questions_from_disk()
        if saved is not None:
            print(f"[store] Loaded {len(saved)} questions from disk.")
            _questions.clear()
            for q in saved:
                _questions[q["id"]] = dict(q)
        else:
            print("[store] No saved questions found — seeding from defaults.")
            _questions.clear()
            for q in defaults:
                _questions[q["id"]] = dict(q)
            _persist_questions()


def get_all_questions() -> List[dict]:
    """Return all questions in insertion order."""
    with _questions_lock:
        return list(_questions.values())


def get_question(question_id: str) -> Optional[dict]:
    """Retrieve a single question by ID."""
    with _questions_lock:
        return _questions.get(question_id)


def save_question(question_id: str, data: dict) -> None:
    """Create or fully replace a question record, then persist to disk."""
    with _questions_lock:
        _questions[question_id] = dict(data)
        _persist_questions()


def delete_question(question_id: str) -> bool:
    """Delete a question and persist the change. Returns True if it existed."""
    with _questions_lock:
        existed = _questions.pop(question_id, None) is not None
        if existed:
            _persist_questions()
        return existed


def save_analysis(analysis_id: str, data: dict) -> None:
    """Save or update an analysis record."""
    with _lock:
        if analysis_id in _store:
            _store[analysis_id].update(data)
            _store[analysis_id]["updated_at"] = datetime.utcnow().isoformat()
        else:
            data.setdefault("created_at", datetime.utcnow().isoformat())
            data.setdefault("updated_at", data["created_at"])
            _store[analysis_id] = data


def get_analysis(analysis_id: str) -> Optional[dict]:
    """Retrieve an analysis record by ID."""
    with _lock:
        return _store.get(analysis_id)


def list_analyses(skip: int = 0, limit: int = 20) -> tuple:
    """Return paginated list of analyses (newest first)."""
    with _lock:
        items = sorted(
            _store.values(),
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )
        return items[skip : skip + limit], len(items)


def delete_analysis(analysis_id: str) -> bool:
    """Delete an analysis record. Returns True if found."""
    with _lock:
        return _store.pop(analysis_id, None) is not None
