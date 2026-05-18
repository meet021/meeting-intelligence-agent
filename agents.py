import os
import json
from anthropic import Anthropic
from tavily import TavilyClient
from dotenv import load_dotenv
from notion_integration import create_meeting_report_in_notion, create_tasks_in_notion

load_dotenv()

client = Anthropic()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def language_detection_agent(transcript: str) -> dict:
    print("🌍 Language Detection Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": f"""Detect the language of this text.
Return ONLY in this exact format:
LANGUAGE: <full language name in English>
CODE: <2-letter ISO code>
IS_ENGLISH: <yes/no>

Text: {transcript[:500]}"""}]
    )
    text = response.content[0].text.strip()
    result = {"language": "English", "code": "en", "is_english": True}
    for line in text.split('\n'):
        if line.startswith("LANGUAGE:"):
            result["language"] = line.replace("LANGUAGE:", "").strip()
        elif line.startswith("CODE:"):
            result["code"] = line.replace("CODE:", "").strip()
        elif line.startswith("IS_ENGLISH:"):
            result["is_english"] = line.replace("IS_ENGLISH:", "").strip().lower() == "yes"
    return result


def translation_agent(transcript: str, source_language: str) -> str:
    print(f"🔄 Translation Agent: {source_language} → English...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": f"""Translate this {source_language} meeting transcript to English.
Keep speaker names as-is. Keep the same format with speaker labels.
Return ONLY the translated text, nothing else.

Transcript:
{transcript}"""}]
    )
    return response.content[0].text.strip()


def analysis_agent(transcript: str) -> dict:
    print("🧠 Analysis Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2500,
        messages=[{"role": "user", "content": f"""You are an expert meeting analyst. Analyze this meeting transcript and extract:

1. A concise summary (3-4 sentences)
2. Key decisions made (list)
3. Action items with owner if mentioned (list)
4. Risks or concerns raised (list)
5. Speakers identified and their roles/contributions (list)

Return your response in this EXACT format:
SUMMARY: <your summary here>
DECISIONS:
- <decision 1>
ACTION_ITEMS:
- <action item 1>
RISKS:
- <risk 1>
SPEAKERS:
- <Speaker Name>: <their main contribution>

Transcript:
{transcript}"""}]
    )
    text = response.content[0].text
    result = {"summary": "", "decisions": [], "action_items": [], "risks": [], "speakers": []}
    lines = text.split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith("SUMMARY:"):
            result["summary"] = line.replace("SUMMARY:", "").strip()
            current_section = None
        elif line == "DECISIONS:":
            current_section = "decisions"
        elif line == "ACTION_ITEMS:":
            current_section = "action_items"
        elif line == "RISKS:":
            current_section = "risks"
        elif line == "SPEAKERS:":
            current_section = "speakers"
        elif line.startswith("- ") and current_section:
            result[current_section].append(line[2:])
    return result


def sentiment_agent(transcript: str) -> dict:
    print("💬 Sentiment Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": f"""Analyze the emotional tone of this meeting transcript.

Return in this EXACT format:
OVERALL: <Positive/Neutral/Negative/Mixed>
SCORE: <1-10>
ENERGY: <High/Medium/Low>
COLLABORATION: <Strong/Moderate/Weak>
KEY_MOMENTS:
- <moment 1>
- <moment 2>
RECOMMENDATION: <one sentence>

Transcript:
{transcript}"""}]
    )
    text = response.content[0].text
    result = {"overall": "Neutral", "score": 5, "energy": "Medium", "collaboration": "Moderate", "key_moments": [], "recommendation": ""}
    lines = text.split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith("OVERALL:"):
            result["overall"] = line.replace("OVERALL:", "").strip()
        elif line.startswith("SCORE:"):
            try:
                result["score"] = int(line.replace("SCORE:", "").strip())
            except:
                result["score"] = 5
        elif line.startswith("ENERGY:"):
            result["energy"] = line.replace("ENERGY:", "").strip()
        elif line.startswith("COLLABORATION:"):
            result["collaboration"] = line.replace("COLLABORATION:", "").strip()
        elif line.startswith("RECOMMENDATION:"):
            result["recommendation"] = line.replace("RECOMMENDATION:", "").strip()
        elif line == "KEY_MOMENTS:":
            current_section = "key_moments"
        elif line.startswith("- ") and current_section == "key_moments":
            result["key_moments"].append(line[2:])
    return result


def productivity_scorer_agent(transcript: str, analysis: dict) -> dict:
    print("📊 Productivity Scorer Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Score this meeting on 6 dimensions (1-10 each).

Return in this EXACT format:
CLARITY: <1-10>
FOCUS: <1-10>
DECISIONS: <1-10>
TIME_EFFICIENCY: <1-10>
PARTICIPATION: <1-10>
NEXT_STEPS: <1-10>
OVERALL_SCORE: <1-100>
GRADE: <A/B/C/D/F>
BIGGEST_STRENGTH: <one sentence>
BIGGEST_WEAKNESS: <one sentence>
COACH_TIP: <one sentence>

Transcript:
{transcript}
Summary: {analysis.get('summary', '')}"""}]
    )
    text = response.content[0].text.strip()
    result = {"clarity": 5, "focus": 5, "decisions": 5, "time_efficiency": 5, "participation": 5, "next_steps": 5, "overall_score": 50, "grade": "C", "biggest_strength": "", "biggest_weakness": "", "coach_tip": ""}
    for line in text.split('\n'):
        line = line.strip()
        try:
            if line.startswith("CLARITY:"):
                result["clarity"] = int(line.replace("CLARITY:", "").strip())
            elif line.startswith("FOCUS:"):
                result["focus"] = int(line.replace("FOCUS:", "").strip())
            elif line.startswith("DECISIONS:"):
                result["decisions"] = int(line.replace("DECISIONS:", "").strip())
            elif line.startswith("TIME_EFFICIENCY:"):
                result["time_efficiency"] = int(line.replace("TIME_EFFICIENCY:", "").strip())
            elif line.startswith("PARTICIPATION:"):
                result["participation"] = int(line.replace("PARTICIPATION:", "").strip())
            elif line.startswith("NEXT_STEPS:"):
                result["next_steps"] = int(line.replace("NEXT_STEPS:", "").strip())
            elif line.startswith("OVERALL_SCORE:"):
                result["overall_score"] = int(line.replace("OVERALL_SCORE:", "").strip())
            elif line.startswith("GRADE:"):
                result["grade"] = line.replace("GRADE:", "").strip()
            elif line.startswith("BIGGEST_STRENGTH:"):
                result["biggest_strength"] = line.replace("BIGGEST_STRENGTH:", "").strip()
            elif line.startswith("BIGGEST_WEAKNESS:"):
                result["biggest_weakness"] = line.replace("BIGGEST_WEAKNESS:", "").strip()
            elif line.startswith("COACH_TIP:"):
                result["coach_tip"] = line.replace("COACH_TIP:", "").strip()
        except:
            pass
    return result


def speaker_analytics_agent(transcript: str, speakers: list) -> dict:
    print("🎙️ Speaker Analytics Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Calculate talk time percentage for each speaker.

Return in this EXACT format for each speaker:
SPEAKER: <name> | WORDS: <count> | PERCENT: <percentage> | STYLE: <Dominant/Balanced/Reserved>

Then:
MOST_VOCAL: <name>
LEAST_VOCAL: <name>
BALANCE_SCORE: <1-10>
INSIGHT: <one sentence>

Transcript:
{transcript}"""}]
    )
    text = response.content[0].text.strip()
    result = {"speakers": [], "most_vocal": "", "least_vocal": "", "balance_score": 5, "insight": ""}
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith("SPEAKER:"):
            try:
                parts = line.split("|")
                name = parts[0].replace("SPEAKER:", "").strip()
                words = int(parts[1].replace("WORDS:", "").strip())
                percent = float(parts[2].replace("PERCENT:", "").strip().replace("%", ""))
                style = parts[3].replace("STYLE:", "").strip()
                result["speakers"].append({"name": name, "words": words, "percent": percent, "style": style})
            except:
                pass
        elif line.startswith("MOST_VOCAL:"):
            result["most_vocal"] = line.replace("MOST_VOCAL:", "").strip()
        elif line.startswith("LEAST_VOCAL:"):
            result["least_vocal"] = line.replace("LEAST_VOCAL:", "").strip()
        elif line.startswith("BALANCE_SCORE:"):
            try:
                result["balance_score"] = int(line.replace("BALANCE_SCORE:", "").strip())
            except:
                result["balance_score"] = 5
        elif line.startswith("INSIGHT:"):
            result["insight"] = line.replace("INSIGHT:", "").strip()
    return result


def smart_alerts_agent(transcript: str, analysis: dict) -> dict:
    print("🔔 Smart Alerts Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Analyze this meeting and generate smart alerts.

Return in this EXACT format:
MEETING_TYPE: <Standup/Planning/Review/Sales/Board/Brainstorm/Other>
WENT_OFF_TOPIC: <yes/no>
HAD_DECISIONS: <yes/no>
HAD_ACTION_ITEMS: <yes/no>
TOO_MANY_SPEAKERS_DOMINATED: <yes/no>
UNRESOLVED_CONFLICTS: <yes/no>
ALERTS:
- <alert 1>
POSITIVE_FLAGS:
- <positive flag 1>
MEETING_HEALTH: <Excellent/Good/Fair/Poor>
HEALTH_REASON: <one sentence>

Summary: {analysis.get('summary', '')}
Transcript:
{transcript}"""}]
    )
    text = response.content[0].text.strip()
    result = {"meeting_type": "Other", "went_off_topic": False, "had_decisions": True, "had_action_items": True, "too_many_speakers_dominated": False, "unresolved_conflicts": False, "alerts": [], "positive_flags": [], "meeting_health": "Good", "health_reason": ""}
    lines = text.split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith("MEETING_TYPE:"):
            result["meeting_type"] = line.replace("MEETING_TYPE:", "").strip()
        elif line.startswith("WENT_OFF_TOPIC:"):
            result["went_off_topic"] = line.replace("WENT_OFF_TOPIC:", "").strip().lower() == "yes"
        elif line.startswith("HAD_DECISIONS:"):
            result["had_decisions"] = line.replace("HAD_DECISIONS:", "").strip().lower() == "yes"
        elif line.startswith("HAD_ACTION_ITEMS:"):
            result["had_action_items"] = line.replace("HAD_ACTION_ITEMS:", "").strip().lower() == "yes"
        elif line.startswith("TOO_MANY_SPEAKERS_DOMINATED:"):
            result["too_many_speakers_dominated"] = line.replace("TOO_MANY_SPEAKERS_DOMINATED:", "").strip().lower() == "yes"
        elif line.startswith("UNRESOLVED_CONFLICTS:"):
            result["unresolved_conflicts"] = line.replace("UNRESOLVED_CONFLICTS:", "").strip().lower() == "yes"
        elif line.startswith("MEETING_HEALTH:"):
            result["meeting_health"] = line.replace("MEETING_HEALTH:", "").strip()
        elif line.startswith("HEALTH_REASON:"):
            result["health_reason"] = line.replace("HEALTH_REASON:", "").strip()
        elif line == "ALERTS:":
            current_section = "alerts"
        elif line == "POSITIVE_FLAGS:":
            current_section = "positive_flags"
        elif line.startswith("- ") and current_section in ["alerts", "positive_flags"]:
            result[current_section].append(line[2:])
    return result


def meeting_cost_calculator(transcript: str, analysis: dict) -> dict:
    print("⏱️ Meeting Cost Calculator running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""Estimate the cost and duration of this meeting.

Return in this EXACT format:
ESTIMATED_DURATION_MINUTES: <number>
PARTICIPANT_COUNT: <number>
AVG_HOURLY_RATE_USD: <number>
TOTAL_COST_USD: <number>
COST_PER_DECISION_USD: <number>
COST_PER_ACTION_ITEM_USD: <number>
ROI_RATING: <Excellent/Good/Fair/Poor>
ROI_REASON: <one sentence>
COULD_BE_EMAIL: <yes/no>
TIME_WASTED_MINUTES: <number>

Speakers: {', '.join(analysis.get('speakers', []))}
Summary: {analysis.get('summary', '')}
Transcript: {transcript[:2000]}"""}]
    )
    text = response.content[0].text.strip()
    result = {"estimated_duration_minutes": 30, "participant_count": 3, "avg_hourly_rate_usd": 75, "total_cost_usd": 112, "cost_per_decision_usd": 0, "cost_per_action_item_usd": 0, "roi_rating": "Good", "roi_reason": "", "could_be_email": False, "time_wasted_minutes": 0}
    for line in text.split('\n'):
        line = line.strip()
        try:
            if line.startswith("ESTIMATED_DURATION_MINUTES:"):
                result["estimated_duration_minutes"] = int(line.replace("ESTIMATED_DURATION_MINUTES:", "").strip())
            elif line.startswith("PARTICIPANT_COUNT:"):
                result["participant_count"] = int(line.replace("PARTICIPANT_COUNT:", "").strip())
            elif line.startswith("AVG_HOURLY_RATE_USD:"):
                result["avg_hourly_rate_usd"] = float(line.replace("AVG_HOURLY_RATE_USD:", "").strip())
            elif line.startswith("TOTAL_COST_USD:"):
                result["total_cost_usd"] = float(line.replace("TOTAL_COST_USD:", "").strip())
            elif line.startswith("COST_PER_DECISION_USD:"):
                result["cost_per_decision_usd"] = float(line.replace("COST_PER_DECISION_USD:", "").strip())
            elif line.startswith("COST_PER_ACTION_ITEM_USD:"):
                result["cost_per_action_item_usd"] = float(line.replace("COST_PER_ACTION_ITEM_USD:", "").strip())
            elif line.startswith("ROI_RATING:"):
                result["roi_rating"] = line.replace("ROI_RATING:", "").strip()
            elif line.startswith("ROI_REASON:"):
                result["roi_reason"] = line.replace("ROI_REASON:", "").strip()
            elif line.startswith("COULD_BE_EMAIL:"):
                result["could_be_email"] = line.replace("COULD_BE_EMAIL:", "").strip().lower() == "yes"
            elif line.startswith("TIME_WASTED_MINUTES:"):
                result["time_wasted_minutes"] = int(line.replace("TIME_WASTED_MINUTES:", "").strip())
        except:
            pass
    return result


def competitor_intelligence_agent(transcript: str) -> dict:
    print("📊 Competitor Intelligence Agent running...")
    detection_response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": f"""Identify any competitor companies or products mentioned.

Return in this EXACT format:
COMPETITORS_MENTIONED: <yes/no>
COMPETITORS:
- <competitor name 1>

If none: COMPETITORS_MENTIONED: no

Transcript:
{transcript}"""}]
    )
    detection_text = detection_response.content[0].text.strip()
    competitors = []
    competitors_mentioned = False
    for line in detection_text.split('\n'):
        line = line.strip()
        if line.startswith("COMPETITORS_MENTIONED:"):
            competitors_mentioned = line.replace("COMPETITORS_MENTIONED:", "").strip().lower() == "yes"
        elif line.startswith("- ") and competitors_mentioned:
            competitors.append(line[2:].strip())
    if not competitors_mentioned or not competitors:
        return {"competitors_found": False, "competitors": []}
    competitor_data = []
    for competitor in competitors[:3]:
        try:
            print(f"   Researching: {competitor}")
            search_results = tavily.search(query=f"{competitor} company AI product features 2025", max_results=3)
            context = "\n".join([f"- {r['title']}: {r['content'][:200]}" for r in search_results.get('results', [])])
            analysis_response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=400,
                messages=[{"role": "user", "content": f"""Competitive brief for {competitor}.

Return in this EXACT format:
DESCRIPTION: <one sentence>
STRENGTHS:
- <strength 1>
WEAKNESSES:
- <weakness 1>
THREAT_LEVEL: <High/Medium/Low>
OUR_ADVANTAGE: <one sentence>

Research:
{context}"""}]
            )
            comp_text = analysis_response.content[0].text.strip()
            comp_data = {"name": competitor, "description": "", "strengths": [], "weaknesses": [], "threat_level": "Medium", "our_advantage": ""}
            current_section = None
            for line in comp_text.split('\n'):
                line = line.strip()
                if line.startswith("DESCRIPTION:"):
                    comp_data["description"] = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("THREAT_LEVEL:"):
                    comp_data["threat_level"] = line.replace("THREAT_LEVEL:", "").strip()
                elif line.startswith("OUR_ADVANTAGE:"):
                    comp_data["our_advantage"] = line.replace("OUR_ADVANTAGE:", "").strip()
                elif line == "STRENGTHS:":
                    current_section = "strengths"
                elif line == "WEAKNESSES:":
                    current_section = "weaknesses"
                elif line.startswith("- ") and current_section in ["strengths", "weaknesses"]:
                    comp_data[current_section].append(line[2:])
            competitor_data.append(comp_data)
        except Exception as e:
            print(f"   Error: {e}")
    return {"competitors_found": True, "competitors": competitor_data}


def memory_agent(transcript: str, analysis: dict) -> dict:
    print("🧠 Memory Agent running...")
    MEMORY_FILE = "meeting_memory.json"
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                memory = json.load(f)
        except:
            memory = {"people": {}, "topics": [], "decisions": [], "context": "", "recurring_themes": []}
    else:
        memory = {"people": {}, "topics": [], "decisions": [], "context": "", "recurring_themes": []}
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Extract key information to remember from this meeting.

Existing context: {json.dumps(memory, indent=2)[:500]}

New meeting summary: {analysis.get('summary', '')}
Speakers: {', '.join(analysis.get('speakers', []))}
Decisions: {', '.join(analysis.get('decisions', []))}

Return in this EXACT format:
NEW_PEOPLE:
- <person name>: <role>
KEY_TOPICS:
- <topic>
IMPORTANT_DECISIONS:
- <decision>
CONTEXT_UPDATE: <2-3 sentences>
RECURRING_THEMES:
- <theme>"""}]
    )
    text = response.content[0].text.strip()
    new_memory = {"new_people": [], "key_topics": [], "important_decisions": [], "context_update": "", "recurring_themes": []}
    lines = text.split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line == "NEW_PEOPLE:":
            current_section = "new_people"
        elif line == "KEY_TOPICS:":
            current_section = "key_topics"
        elif line == "IMPORTANT_DECISIONS:":
            current_section = "important_decisions"
        elif line.startswith("CONTEXT_UPDATE:"):
            new_memory["context_update"] = line.replace("CONTEXT_UPDATE:", "").strip()
            current_section = None
        elif line == "RECURRING_THEMES:":
            current_section = "recurring_themes"
        elif line.startswith("- ") and current_section:
            new_memory[current_section].append(line[2:])
    for person in new_memory["new_people"]:
        if ":" in person:
            name, role = person.split(":", 1)
            memory["people"][name.strip()] = role.strip()
    memory["topics"] = list(set(memory.get("topics", []) + new_memory["key_topics"]))[-20:]
    memory["decisions"] = list(set(memory.get("decisions", []) + new_memory["important_decisions"]))[-20:]
    memory["recurring_themes"] = list(set(memory.get("recurring_themes", []) + new_memory["recurring_themes"]))[-10:]
    if new_memory["context_update"]:
        memory["context"] = new_memory["context_update"]
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)
    print(f"✅ Memory updated — {len(memory['people'])} people, {len(memory['topics'])} topics")
    new_memory["full_memory"] = memory
    return new_memory


def smart_action_assigner(analysis: dict) -> list:
    print("🎯 Smart Action Assigner running...")
    if not analysis.get("action_items"):
        return []
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": f"""Assign each action item to the most likely owner.

Speakers: {', '.join(analysis.get('speakers', []))}
Summary: {analysis.get('summary', '')}

Action items:
{chr(10).join([f"- {item}" for item in analysis.get('action_items', [])])}

Return in this EXACT format for each action item:
ACTION: <action item text>
OWNER: <person name or Team>
PRIORITY: <High/Medium/Low>
DUE: <e.g. By Friday, Next week>
CATEGORY: <Budget/Technical/Marketing/HR/Strategy/Other>

Repeat for each action item."""}]
    )
    text = response.content[0].text.strip()
    assigned = []
    current = {}
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith("ACTION:"):
            if current:
                assigned.append(current)
            current = {"action": line.replace("ACTION:", "").strip(), "owner": "Team", "priority": "Medium", "due": "Next week", "category": "Other"}
        elif line.startswith("OWNER:"):
            current["owner"] = line.replace("OWNER:", "").strip()
        elif line.startswith("PRIORITY:"):
            current["priority"] = line.replace("PRIORITY:", "").strip()
        elif line.startswith("DUE:"):
            current["due"] = line.replace("DUE:", "").strip()
        elif line.startswith("CATEGORY:"):
            current["category"] = line.replace("CATEGORY:", "").strip()
    if current:
        assigned.append(current)
    print(f"✅ Assigned {len(assigned)} action items")
    return assigned


def trend_analyzer_agent(history: list) -> dict:
    print("📈 Trend Analyzer Agent running...")
    if len(history) < 2:
        return {}
    meetings_summary = []
    for i, m in enumerate(history):
        meetings_summary.append(
            f"Meeting {i+1} ({m.get('date', 'N/A')}): "
            f"Productivity={m.get('productivity_score', 0)}/100, "
            f"Sentiment={m.get('sentiment_score', 0)}/10, "
            f"Decisions={m.get('decisions_count', 0)}, "
            f"Actions={m.get('action_items_count', 0)}, "
            f"Language={m.get('language', 'English')}"
        )
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": f"""Analyze trends across multiple meetings.

Meeting history:
{chr(10).join(meetings_summary)}

Return in this EXACT format:
PRODUCTIVITY_TREND: <Improving/Declining/Stable/Fluctuating>
SENTIMENT_TREND: <Improving/Declining/Stable/Fluctuating>
BEST_DAY_PATTERN: <observation>
WORST_PATTERN: <observation>
TOP_STRENGTH: <biggest consistent strength>
TOP_WEAKNESS: <biggest consistent weakness>
PATTERNS:
- <pattern 1>
- <pattern 2>
- <pattern 3>
RECOMMENDATIONS:
- <recommendation 1>
- <recommendation 2>
- <recommendation 3>
PREDICTION: <one sentence prediction>
OVERALL_HEALTH: <Excellent/Good/Fair/Poor>
HEALTH_REASON: <one sentence>"""}]
    )
    text = response.content[0].text.strip()
    result = {"productivity_trend": "Stable", "sentiment_trend": "Stable", "best_day_pattern": "", "worst_pattern": "", "top_strength": "", "top_weakness": "", "patterns": [], "recommendations": [], "prediction": "", "overall_health": "Good", "health_reason": ""}
    lines = text.split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith("PRODUCTIVITY_TREND:"):
            result["productivity_trend"] = line.replace("PRODUCTIVITY_TREND:", "").strip()
        elif line.startswith("SENTIMENT_TREND:"):
            result["sentiment_trend"] = line.replace("SENTIMENT_TREND:", "").strip()
        elif line.startswith("BEST_DAY_PATTERN:"):
            result["best_day_pattern"] = line.replace("BEST_DAY_PATTERN:", "").strip()
        elif line.startswith("WORST_PATTERN:"):
            result["worst_pattern"] = line.replace("WORST_PATTERN:", "").strip()
        elif line.startswith("TOP_STRENGTH:"):
            result["top_strength"] = line.replace("TOP_STRENGTH:", "").strip()
        elif line.startswith("TOP_WEAKNESS:"):
            result["top_weakness"] = line.replace("TOP_WEAKNESS:", "").strip()
        elif line.startswith("PREDICTION:"):
            result["prediction"] = line.replace("PREDICTION:", "").strip()
        elif line.startswith("OVERALL_HEALTH:"):
            result["overall_health"] = line.replace("OVERALL_HEALTH:", "").strip()
        elif line.startswith("HEALTH_REASON:"):
            result["health_reason"] = line.replace("HEALTH_REASON:", "").strip()
        elif line == "PATTERNS:":
            current_section = "patterns"
        elif line == "RECOMMENDATIONS:":
            current_section = "recommendations"
        elif line.startswith("- ") and current_section in ["patterns", "recommendations"]:
            result[current_section].append(line[2:])
    return result


def next_meeting_predictor_agent(history: list, current_analysis: dict) -> dict:
    """Predict topics, risks and agenda for the next meeting."""
    print("🔮 Next Meeting Predictor running...")

    if not history and not current_analysis:
        return {}

    # Build context from history and current meeting
    history_context = []
    for i, m in enumerate(history[-5:]):  # Last 5 meetings
        history_context.append(
            f"Meeting {i+1} ({m.get('date', 'N/A')}): "
            f"Summary: {m.get('summary', '')[:200]}"
        )

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": f"""You are an expert meeting strategist.
Based on past meetings and the current meeting analysis, predict what the NEXT meeting should cover.

RECENT MEETING HISTORY:
{chr(10).join(history_context) if history_context else 'No history available'}

CURRENT MEETING:
Summary: {current_analysis.get('summary', '')}
Decisions: {', '.join(current_analysis.get('decisions', []))}
Action Items: {', '.join(current_analysis.get('action_items', []))}
Risks: {', '.join(current_analysis.get('risks', []))}
Unresolved: {current_analysis.get('alerts', {}).get('alerts', [])}

Return in this EXACT format:
PREDICTED_TOPICS:
- <topic 1 likely to come up>
- <topic 2>
- <topic 3>
- <topic 4>
PREDICTED_RISKS:
- <risk 1 to watch out for>
- <risk 2>
SUGGESTED_AGENDA:
- <agenda item 1>
- <agenda item 2>
- <agenda item 3>
- <agenda item 4>
- <agenda item 5>
FOLLOWUP_ITEMS:
- <item that needs follow-up from this meeting>
- <item 2>
RECOMMENDED_ATTENDEES:
- <person/role who should attend>
- <person/role 2>
SUGGESTED_DURATION: <e.g. 30 minutes, 1 hour>
MEETING_TYPE_SUGGESTION: <e.g. Decision Meeting, Review, Standup>
PREPARATION_TIPS:
- <tip 1 to prepare better>
- <tip 2>
CONFIDENCE_SCORE: <1-10 how confident this prediction is>"""}]
    )

    text = response.content[0].text.strip()
    result = {
        "predicted_topics": [],
        "predicted_risks": [],
        "suggested_agenda": [],
        "followup_items": [],
        "recommended_attendees": [],
        "suggested_duration": "1 hour",
        "meeting_type_suggestion": "Planning",
        "preparation_tips": [],
        "confidence_score": 7
    }

    lines = text.split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if line == "PREDICTED_TOPICS:":
            current_section = "predicted_topics"
        elif line == "PREDICTED_RISKS:":
            current_section = "predicted_risks"
        elif line == "SUGGESTED_AGENDA:":
            current_section = "suggested_agenda"
        elif line == "FOLLOWUP_ITEMS:":
            current_section = "followup_items"
        elif line == "RECOMMENDED_ATTENDEES:":
            current_section = "recommended_attendees"
        elif line == "PREPARATION_TIPS:":
            current_section = "preparation_tips"
        elif line.startswith("SUGGESTED_DURATION:"):
            result["suggested_duration"] = line.replace("SUGGESTED_DURATION:", "").strip()
            current_section = None
        elif line.startswith("MEETING_TYPE_SUGGESTION:"):
            result["meeting_type_suggestion"] = line.replace("MEETING_TYPE_SUGGESTION:", "").strip()
            current_section = None
        elif line.startswith("CONFIDENCE_SCORE:"):
            try:
                result["confidence_score"] = int(line.replace("CONFIDENCE_SCORE:", "").strip())
            except:
                result["confidence_score"] = 7
            current_section = None
        elif line.startswith("- ") and current_section:
            result[current_section].append(line[2:])

    return result


def compare_meetings_agent(analysis1: dict, analysis2: dict) -> dict:
    print("🔄 Meeting Comparison Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": f"""Compare these two meetings and provide insights.

MEETING 1:
Summary: {analysis1.get('summary', '')}
Productivity: {analysis1.get('productivity', {}).get('overall_score', 0)}/100
Sentiment: {analysis1.get('sentiment', {}).get('score', 5)}/10
Decisions: {len(analysis1.get('decisions', []))}
Action Items: {len(analysis1.get('action_items', []))}

MEETING 2:
Summary: {analysis2.get('summary', '')}
Productivity: {analysis2.get('productivity', {}).get('overall_score', 0)}/100
Sentiment: {analysis2.get('sentiment', {}).get('score', 5)}/10
Decisions: {len(analysis2.get('decisions', []))}
Action Items: {len(analysis2.get('action_items', []))}

Return in this EXACT format:
BETTER_MEETING: <1 or 2>
BETTER_REASON: <one sentence>
IMPROVEMENT_AREAS:
- <area 1>
- <area 2>
COMMON_THEMES:
- <theme 1>
OVERALL_INSIGHT: <2-3 sentences>
RECOMMENDATION: <one sentence>"""}]
    )
    text = response.content[0].text.strip()
    result = {"better_meeting": "1", "better_reason": "", "improvement_areas": [], "common_themes": [], "overall_insight": "", "recommendation": ""}
    lines = text.split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith("BETTER_MEETING:"):
            result["better_meeting"] = line.replace("BETTER_MEETING:", "").strip()
        elif line.startswith("BETTER_REASON:"):
            result["better_reason"] = line.replace("BETTER_REASON:", "").strip()
        elif line.startswith("OVERALL_INSIGHT:"):
            result["overall_insight"] = line.replace("OVERALL_INSIGHT:", "").strip()
        elif line.startswith("RECOMMENDATION:"):
            result["recommendation"] = line.replace("RECOMMENDATION:", "").strip()
        elif line == "IMPROVEMENT_AREAS:":
            current_section = "improvement_areas"
        elif line == "COMMON_THEMES:":
            current_section = "common_themes"
        elif line.startswith("- ") and current_section in ["improvement_areas", "common_themes"]:
            result[current_section].append(line[2:])
    return result


def qa_agent(question: str, transcript: str, analysis: dict) -> str:
    print(f"🧠 Q&A Agent: {question}")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""Answer this question about the meeting accurately and concisely.

SUMMARY: {analysis.get('summary', '')}
DECISIONS: {', '.join(analysis.get('decisions', []))}
ACTION ITEMS: {', '.join(analysis.get('action_items', []))}
SPEAKERS: {', '.join(analysis.get('speakers', []))}

TRANSCRIPT:
{transcript}

QUESTION: {question}

Answer:"""}]
    )
    return response.content[0].text.strip()


def research_agent(analysis: dict) -> str:
    print("🔍 Research Agent running...")
    topics_response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": f"""Identify the ONE most important topic for external research.
Return ONLY the search query, nothing else.

Summary: {analysis.get('summary', '')}
Decisions: {', '.join(analysis.get('decisions', []))}"""}]
    )
    search_query = topics_response.content[0].text.strip()
    print(f"   Searching for: {search_query}")
    try:
        search_results = tavily.search(query=search_query, max_results=3)
        context = "\n".join([f"- {r['title']}: {r['content'][:200]}" for r in search_results.get('results', [])])
    except Exception as e:
        context = f"Search unavailable: {str(e)}"
    summary_response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": f"""Summarize this research in 2-3 sentences relevant to the meeting:

Query: {search_query}
Results: {context}"""}]
    )
    return summary_response.content[0].text.strip()


def action_agent(analysis: dict) -> str:
    print("📧 Action Agent running...")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""Write a professional follow-up email for this meeting.
Include: greeting, recap, action items with owners, next steps, sign-off.

Summary: {analysis.get('summary', '')}
Decisions: {', '.join(analysis.get('decisions', []))}
Action Items: {', '.join(analysis.get('action_items', []))}
Speakers: {', '.join(analysis.get('speakers', []))}"""}]
    )
    return response.content[0].text.strip()


def orchestrator_agent(transcript: str) -> dict:
    print("🎯 Orchestrator starting pipeline...\n")

    lang_info = language_detection_agent(transcript)
    print(f"   Detected language: {lang_info['language']}")

    original_transcript = transcript
    if not lang_info["is_english"]:
        transcript = translation_agent(transcript, lang_info["language"])
        print("   Translated to English!")

    analysis = analysis_agent(transcript)
    analysis["language_info"] = lang_info
    analysis["original_transcript"] = original_transcript
    analysis["translated_transcript"] = transcript if not lang_info["is_english"] else None

    analysis["sentiment"] = sentiment_agent(transcript)
    analysis["productivity"] = productivity_scorer_agent(transcript, analysis)
    analysis["speaker_analytics"] = speaker_analytics_agent(transcript, analysis.get("speakers", []))
    analysis["alerts"] = smart_alerts_agent(transcript, analysis)
    analysis["cost"] = meeting_cost_calculator(transcript, analysis)
    analysis["competitor_intel"] = competitor_intelligence_agent(transcript)
    analysis["memory"] = memory_agent(transcript, analysis)
    analysis["research"] = research_agent(analysis)
    analysis["follow_up_email"] = action_agent(analysis)
    analysis["assigned_actions"] = smart_action_assigner(analysis)

    # Next meeting prediction
    from history import load_history
    history = load_history()
    analysis["next_meeting_prediction"] = next_meeting_predictor_agent(history, analysis)

    notion_url = create_meeting_report_in_notion(analysis)
    analysis["notion_url"] = notion_url

    if analysis.get("action_items"):
        task_results = create_tasks_in_notion(analysis["action_items"], analysis.get("summary", ""))
        analysis["task_results"] = task_results

    print("\n✅ All agents completed!")
    return analysis