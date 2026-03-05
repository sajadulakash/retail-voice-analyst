"""
In-memory store for analysis results.
Simple thread-safe dictionary to hold results without a database.
"""

import threading
from datetime import datetime
from typing import Dict, Optional

_lock = threading.Lock()
_store: Dict[str, dict] = {}


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
