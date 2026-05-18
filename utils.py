import os
import tempfile
import whisper
from dotenv import load_dotenv

load_dotenv()


def transcribe_audio(file_path: str) -> str:
    """Transcribe audio/video file to text using Whisper."""
    print("🎙️ Transcribing audio...")
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]


def save_uploaded_file(uploaded_file) -> str:
    """Save Streamlit uploaded file to a temp path and return path."""
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(uploaded_file.read())
        return f.name


def get_sentiment_emoji(overall: str) -> str:
    """Return emoji for sentiment."""
    mapping = {
        "Positive": "😊",
        "Negative": "😟",
        "Neutral": "😐",
        "Mixed": "🤔"
    }
    return mapping.get(overall, "😐")


def get_score_color(score: int) -> str:
    """Return color based on sentiment score."""
    if score >= 7:
        return "green"
    elif score >= 4:
        return "orange"
    else:
        return "red"


def format_report(analysis: dict) -> str:
    """Format the final report as markdown."""
    report = []
    report.append("# 📋 Meeting Intelligence Report\n")

    if analysis.get("summary"):
        report.append("## 📝 Summary")
        report.append(analysis["summary"] + "\n")

    if analysis.get("speakers"):
        report.append("## 👥 Speakers")
        for s in analysis["speakers"]:
            report.append(f"- {s}")
        report.append("")

    if analysis.get("decisions"):
        report.append("## ✅ Key Decisions")
        for d in analysis["decisions"]:
            report.append(f"- {d}")
        report.append("")

    if analysis.get("action_items"):
        report.append("## 🎯 Action Items")
        for item in analysis["action_items"]:
            report.append(f"- {item}")
        report.append("")

    if analysis.get("sentiment"):
        s = analysis["sentiment"]
        report.append("## 💬 Sentiment Analysis")
        report.append(f"- Overall: {s.get('overall', 'N/A')}")
        report.append(f"- Score: {s.get('score', 'N/A')}/10")
        report.append(f"- Energy: {s.get('energy', 'N/A')}")
        report.append(f"- Collaboration: {s.get('collaboration', 'N/A')}")
        report.append(f"- Recommendation: {s.get('recommendation', 'N/A')}")
        report.append("")

    if analysis.get("research"):
        report.append("## 🔍 Research & Context")
        report.append(analysis["research"] + "\n")

    if analysis.get("follow_up_email"):
        report.append("## 📧 Follow-up Email Draft")
        report.append(analysis["follow_up_email"] + "\n")

    if analysis.get("risks"):
        report.append("## ⚠️ Risks & Concerns")
        for r in analysis["risks"]:
            report.append(f"- {r}")

    return "\n".join(report)