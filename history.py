import json
import os
from datetime import datetime


HISTORY_FILE = "meeting_history.json"


def save_meeting_to_history(analysis: dict, transcript: str) -> None:
    """Save meeting analysis to local history file."""
    history = load_history()

    meeting = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "date": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "summary": analysis.get("summary", ""),
        "language": analysis.get("language_info", {}).get("language", "English"),
        "speakers_count": len(analysis.get("speakers", [])),
        "decisions_count": len(analysis.get("decisions", [])),
        "action_items_count": len(analysis.get("action_items", [])),
        "sentiment_score": analysis.get("sentiment", {}).get("score", 5),
        "sentiment_overall": analysis.get("sentiment", {}).get("overall", "Neutral"),
        "productivity_score": analysis.get("productivity", {}).get("overall_score", 50),
        "productivity_grade": analysis.get("productivity", {}).get("grade", "C"),
        "notion_url": analysis.get("notion_url", ""),
        "transcript_preview": transcript[:200] + "..." if len(transcript) > 200 else transcript
    }

    history.append(meeting)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    print(f"📚 Meeting saved to history (total: {len(history)})")


def load_history() -> list:
    """Load meeting history from file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def get_history_stats(history: list) -> dict:
    """Calculate stats across all meetings."""
    if not history:
        return {}

    avg_productivity = sum(m.get("productivity_score", 0) for m in history) / len(history)
    avg_sentiment = sum(m.get("sentiment_score", 0) for m in history) / len(history)
    total_decisions = sum(m.get("decisions_count", 0) for m in history)
    total_actions = sum(m.get("action_items_count", 0) for m in history)

    grades = [m.get("productivity_grade", "C") for m in history]
    most_common_grade = max(set(grades), key=grades.count)

    return {
        "total_meetings": len(history),
        "avg_productivity": round(avg_productivity, 1),
        "avg_sentiment": round(avg_sentiment, 1),
        "total_decisions": total_decisions,
        "total_actions": total_actions,
        "most_common_grade": most_common_grade,
        "best_meeting": max(history, key=lambda x: x.get("productivity_score", 0)),
        "latest_meeting": history[-1] if history else None
    }