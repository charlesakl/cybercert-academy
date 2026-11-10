"""Versioned serialization for the student's durable learning record."""
from __future__ import annotations
from datetime import date
from typing import Any

VERSION = 1


def serialize(state: Any) -> dict:
    reviews = {}
    for card_id, review in state.get("flashcard_reviews", {}).items():
        due = review.get("due", date.today())
        reviews[card_id] = {"due": due.isoformat() if isinstance(due, date) else str(due),
                            "step": int(review.get("step", 0))}
    return {
        "version": VERSION,
        "completed": sorted(state.get("completed", set())),
        "current_lesson": state.get("current_lesson"),
        "practice_history": state.get("practice_history", []),
        "flashcard_reviews": reviews,
        "activity_days": sorted(set(state.get("activity_days", []))),
        "ai_daily_usage": dict(state.get("ai_daily_usage", {})),
    }


def deserialize(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("version", VERSION) != VERSION:
        raise ValueError("Unsupported saved progress format")
    reviews = {}
    for card_id, review in payload.get("flashcard_reviews", {}).items():
        reviews[card_id] = {"due": date.fromisoformat(review["due"]), "step": int(review["step"])}
    return {
        "completed": set(payload.get("completed", [])),
        "current_lesson": payload.get("current_lesson"),
        "practice_history": list(payload.get("practice_history", [])),
        "flashcard_reviews": reviews,
        "activity_days": list(payload.get("activity_days", [])),
        "ai_daily_usage": dict(payload.get("ai_daily_usage", {})),
    }
