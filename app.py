import streamlit as st
import os
import json
import time
import threading
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from utils import (transcribe_audio, save_uploaded_file,
                   format_report, get_sentiment_emoji, get_score_color)
from agents import orchestrator_agent, qa_agent, compare_meetings_agent, trend_analyzer_agent
from history import save_meeting_to_history, load_history, get_history_stats
from wordcloud_generator import generate_wordcloud, get_top_words
from pdf_generator import build_pdf_report


try:
    
        get_google_auth_url, exchange_code_for_token, is_google_connected,
        disconnect_google, get_upcoming_meetings, get_past_meetings,
        get_meet_recordings, download_recording, get_google_credentials_status,
        get_connected_email
    )
    GOOGLE_AVAILABLE = True
except Exception as e:
    print(f"Google integration unavailable: {e}")
    GOOGLE_AVAILABLE = False

st.set_page_config(page_title="Meeting Intelligence Agent", page_icon="🤖", layout="wide")

query_params = st.query_params
if "code" in query_params and GOOGLE_AVAILABLE:
    code = query_params["code"]
    if exchange_code_for_token(code):
        st.session_state.google_just_connected = True
    st.query_params.clear()

if "analysis" not in st.session_state: st.session_state.analysis = None
if "report" not in st.session_state: st.session_state.report = None
if "transcript" not in st.session_state: st.session_state.transcript = None
if "checkboxes" not in st.session_state: st.session_state.checkboxes = {}
if "qa_history" not in st.session_state: st.session_state.qa_history = []
if "selected_template" not in st.session_state: st.session_state.selected_template = None
if "comparison_result" not in st.session_state: st.session_state.comparison_result = None
if "recorder" not in st.session_state: st.session_state.recorder = None
if "is_recording" not in st.session_state: st.session_state.is_recording = False
if "recorded_file" not in st.session_state: st.session_state.recorded_file = None
if "recording_duration" not in st.session_state: st.session_state.recording_duration = 0
if "trends" not in st.session_state: st.session_state.trends = None
if "google_just_connected" not in st.session_state: st.session_state.google_just_connected = False

TEMPLATES = {
    "None": "",
    "📋 Daily Standup": """John (Engineering Lead): Good morning team! Yesterday I completed the user authentication module. Today I'll work on the API integration. No blockers.
Sarah (Designer): Hi everyone! Yesterday I finished the dashboard mockups. Today I'm working on mobile responsive designs. I need feedback by EOD.
Mike (Backend Dev): Morning! Yesterday I fixed 3 critical bugs. Today I'll deploy the hotfix to production. Blocker - I need DevOps access to staging server.
Lisa (PM): Good morning! Yesterday I had stakeholder calls. Today I'm writing user stories for Sprint 15. No blockers. Sprint review is Friday 2 PM.
John: We're on track for release next Tuesday. Mike please send staging access request.""",
    "💼 Sales Call": """Alex (Sales Rep): Hi David, thanks for your time. I wanted to show how our platform helps TechCorp reduce meeting overhead by 60%.
David (Prospect): We're definitely struggling with meeting efficiency. Too much time in meetings and following up afterwards.
Alex: Our AI agent automatically transcribes, summarizes and creates action items from every meeting. It integrates directly with Notion.
David: Interesting. What's the pricing and implementation time?
Alex: Three tiers starting at $99/month for 10 users. Implementation takes less than a day.
David: My main concern is data security. Where is data stored?
Alex: All data is encrypted at rest and in transit. We're SOC 2 compliant.
David: Can you send a proposal by Thursday? I need to share with our CTO.
Alex: Absolutely! Detailed proposal with security docs by Wednesday EOD.""",
    "🏛️ Board Meeting": """Chairman (Robert): Q2 board meeting to order. Agenda: financial results, strategic initiatives, risk review.
CFO (Jennifer): Q2 revenue $4.2M, up 34% YoY. EBITDA margin 18%. Raising full year guidance to $16M.
CEO (Michael): Successfully entered three new markets. CAC dropped 22%. On track for 10,000 enterprise customers.
Board Member (Patricia): What's our biggest Q3 risk?
CEO (Michael): New competitor with significant VC backing. Responding with accelerated roadmap and $500K R&D investment.
Chairman (Robert): Board approves Q3 R&D budget. Jennifer prepare cash flow analysis. Next meeting August 15th.""",
    "🚀 Product Launch": """Emma (PM): Finalizing ProductX launch plan for June 20th. Three weeks to go.
Tom (Dev Lead): Engineering 90% complete. Code complete by June 10th.
Lisa (Marketing): Campaign ready. 50,000 subscriber email sequences scheduled. Targeting 1,000 day-one signups.
Ryan (Sales): 45 prospects in pipeline. Confident converting 20 in first month - $180K ARR.
Emma: Launch confirmed June 20th. Tom QA by June 15th. Lisa brief support June 12th. Ryan sales enablement June 14th.""",
    "🔄 Sprint Retro": """Anna (Scrum Master): Sprint 23 retro. What went well, what did not, action items.
Chris (Dev): Shipped payment integration on time. Code review much improved.
Maya (Designer): Design-engineering collaboration smoother. Daily syncs helped.
James (Dev): Too many mid-sprint scope changes. Three features added after planning.
Rachel (PM): Fair feedback. I will propose scope freeze 48 hours after sprint planning.
Anna: Actions - Rachel implements scope freeze. James works with DevOps on SLA. Velocity 42 points, up from 35."""
}

AGENTS_LIST = [
    ("🌍", "Language Detection", "Detecting language..."),
    ("🔄", "Translation", "Translating if needed..."),
    ("🧠", "Analysis", "Extracting decisions and actions..."),
    ("💬", "Sentiment", "Reading emotional tone..."),
    ("📊", "Productivity", "Scoring 6 dimensions..."),
    ("🎙️", "Speaker Analytics", "Analyzing talk time..."),
    ("🔔", "Smart Alerts", "Detecting issues..."),
    ("⏱️", "Cost Calculator", "Calculating ROI..."),
    ("📊", "Competitor Intel", "Researching competitors..."),
    ("🧠", "Memory Agent", "Updating memory..."),
    ("🔍", "Research", "Searching the web..."),
    ("📧", "Email Drafter", "Writing follow-up..."),
    ("🎯", "Action Assigner", "Assigning priorities..."),
    ("📧", "Email Personalizer", "Writing personal emails..."),
    ("🔮", "Next Predictor", "Predicting next meeting..."),
    ("📋", "Notion", "Saving to Notion...")
]

st.sidebar.title("🤖 Meeting Agent")
page = st.sidebar.selectbox("Navigate", [
    "🤖 Analyze Meeting", "📅 Google Integration",
    "🔄 Compare Meetings", "📚 Meeting History",
    "🏆 Leaderboard", "📈 Trend Analyzer"
], index=0)

st.sidebar.divider()
st.sidebar.markdown("### 🔗 Integrations")
google_connected = GOOGLE_AVAILABLE and is_google_connected()
if google_connected:
    try:
        email = get_connected_email()
        st.sidebar.success(f"🟢 Google: {email[:25]}" if len(email) > 25 else f"🟢 Google: {email}")
    except:
        st.sidebar.success("🟢 Google Connected")
else:
    st.sidebar.info("🔴 Google: Not connected")
st.sidebar.caption("Go to 📅 Google Integration to connect")

st.sidebar.divider()
st.sidebar.markdown("### 🏆 Powered by")
st.sidebar.markdown("- Claude Sonnet (Anthropic)\n- OpenAI Whisper\n- Tavily Search\n- Google Calendar & Drive\n- Notion API")

st.sidebar.divider()
st.sidebar.markdown("### 📊 Quick Stats")
history = load_history()
stats = get_history_stats(history)
if stats:
    st.sidebar.metric("Meetings Analyzed", stats.get("total_meetings", 0))
    st.sidebar.metric("Avg Productivity", f"{stats.get('avg_productivity', 0)}/100")
    st.sidebar.metric("Total Action Items", stats.get("total_actions", 0))
else:
    st.sidebar.info("No meetings analyzed yet")

if page == "📅 Google Integration":
    st.title("📅 Google Calendar & Meet Integration")
    st.caption("Connect your Google account to import meetings and recordings automatically")
    st.divider()

    if st.session_state.google_just_connected:
        st.success("✅ Google account connected successfully!")
        st.session_state.google_just_connected = False

    if not GOOGLE_AVAILABLE:
        st.warning("⚠️ Google integration unavailable. Check google_credentials.json.")
    else:
        try:
            g_status = get_google_credentials_status()
        except:
            g_status = {"credentials_file": False, "connected": False, "email": "", "error": ""}

        if not g_status["credentials_file"]:
            st.error("❌ google_credentials.json not found in project folder.")
        elif not g_status["connected"]:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### What you get after connecting:")
                st.markdown("- 📅 See all upcoming meetings from Google Calendar\n- 📋 Browse past meetings from last 30-90 days\n- 📹 Import Google Meet recordings with one click\n- 🚀 Analyze any recording with 16 AI agents instantly\n- 👥 See attendee list automatically from Calendar")
            with col2:
                auth_url = get_google_auth_url()
                if auth_url:
                    st.link_button("🔵 Connect Google Account", auth_url, use_container_width=True)
                    st.caption("Redirects to Google login")
                else:
                    st.error("Could not generate auth URL")
        else:
            email = g_status.get("email", "")
            st.success(f"✅ Connected as **{email}**" if email else "✅ Google Connected!")
            if st.button("🔴 Disconnect Google"):
                disconnect_google()
                st.rerun()

            st.divider()
            gtab1, gtab2, gtab3 = st.tabs(["📅 Upcoming Meetings", "📋 Past Meetings", "📹 Meet Recordings"])

            with gtab1:
                st.markdown("### 📅 Your Upcoming Meetings")
                days_ahead = st.slider("Days ahead:", 3, 30, 14, key="gcal_days_ahead")
                with st.spinner("Loading your calendar..."):
                    upcoming = get_upcoming_meetings(days_ahead=days_ahead)
                if upcoming:
                    video_count = sum(1 for m in upcoming if m.get("is_video"))
                    st.info(f"📊 {len(upcoming)} meetings | 📹 {video_count} video meetings")
                    for meeting in upcoming:
                        icon = "📹" if meeting.get("is_video") else "📅"
                        start_clean = meeting["start"][:16].replace("T", " ") if meeting.get("start") else "N/A"
                        with st.expander(f"{icon} **{meeting['title']}** — {start_clean} | 👥 {meeting.get('attendee_count', 0)} attendees"):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"**Start:** {start_clean}")
                                st.markdown(f"**Attendees:** {meeting.get('attendee_count', 0)}")
                                st.markdown(f"**Organizer:** {meeting.get('organizer', 'N/A')}")
                            with c2:
                                if meeting.get("meet_link"):
                                    st.link_button("🔗 Join Google Meet", meeting["meet_link"], use_container_width=True)
                            if meeting.get("attendees"):
                                st.markdown(f"**Emails:** {', '.join(meeting['attendees'][:5])}")
                            if meeting.get("description"):
                                st.markdown(f"**Notes:** {meeting['description'][:200]}")
                else:
                    st.info(f"No upcoming meetings in the next {days_ahead} days")

            with gtab2:
                st.markdown("### 📋 Past Meetings")
                days_back = st.slider("Days to look back:", 7, 90, 30, key="gcal_days_back")
                with st.spinner("Loading past meetings..."):
                    past = get_past_meetings(days_back=days_back)
                if past:
                    video_meetings = [m for m in past if m.get("is_video")]
                    st.info(f"📊 {len(past)} total | 📹 {len(video_meetings)} video meetings")
                    for meeting in reversed(past[-20:]):
                        icon = "📹" if meeting.get("is_video") else "📅"
                        start_clean = meeting["start"][:16].replace("T", " ") if meeting.get("start") else "N/A"
                        with st.expander(f"{icon} **{meeting['title']}** — {start_clean}"):
                            st.markdown(f"**Start:** {start_clean}")
                            st.markdown(f"**Attendees:** {meeting.get('attendee_count', 0)}")
                            if meeting.get("attendees"):
                                st.markdown(f"**Emails:** {', '.join(meeting['attendees'][:5])}")
                else:
                    st.info("No past meetings found")

            with gtab3:
                st.markdown("### 📹 Google Meet Recordings")
                st.caption("Recordings auto-saved to Google Drive when you record in Meet")
                days_rec = st.slider("Days to look back:", 7, 90, 30, key="gdrive_days_back")
                with st.spinner("Searching Google Drive..."):
                    recordings = get_meet_recordings(days_back=days_rec)
                if recordings:
                    st.success(f"✅ Found {len(recordings)} recording(s)")
                    for rec in recordings:
                        created_clean = rec["created"][:10] if rec.get("created") else "N/A"
                        with st.expander(f"📹 **{rec['name']}** — {rec['size_mb']} MB — {created_clean}"):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"**Created:** {created_clean}")
                                st.markdown(f"**Size:** {rec['size_mb']} MB")
                            with c2:
                                if rec.get("view_link"):
                                    st.link_button("📹 View in Drive", rec["view_link"], use_container_width=True)
                            if st.button("🚀 Download and Analyze with 16 Agents", key=f"analyze_gdrive_{rec['id']}", use_container_width=True, type="primary"):
                                with st.spinner(f"⬇️ Downloading {rec['name']}..."):
                                    file_path = download_recording(rec["id"], rec["name"])
                                if file_path and os.path.exists(file_path):
                                    with st.spinner("🎙️ Transcribing with Whisper..."):
                                        try:
                                            transcript = transcribe_audio(file_path)
                                            os.unlink(file_path)
                                            st.session_state.transcript = transcript
                                            st.session_state.analysis = None
                                            st.success("✅ Done! Go to 🤖 Analyze Meeting tab.")
                                            with st.expander("👀 Preview"):
                                                st.write(transcript[:800] + "...")
                                        except Exception as e:
                                            st.error(f"Transcription error: {e}")
                                else:
                                    st.error("❌ Download failed.")
                else:
                    st.info("No recordings found. To record a Google Meet: Start Meet → click menu → Record meeting → saves to Drive automatically.")

elif page == "🤖 Analyze Meeting":
    st.title("🤖 Meeting Intelligence Agent")
    st.caption("Upload, record live, import from Google Meet, or paste transcript → 16 AI agents analyze everything")
    st.divider()

    if st.session_state.transcript and not st.session_state.analysis:
        st.success("✅ Transcript imported! Click Analyze to process.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📁 Upload Meeting")
        uploaded_file = st.file_uploader("Upload audio or video file", type=["mp3", "mp4", "wav", "m4a", "ogg", "webm"])

        st.subheader("🎙️ Or Record Live")
        if is_microphone_available():
            mics = get_available_microphones()
            if mics:
                st.caption(f"🎤 {len(mics)} microphone(s) detected")
            rec_col1, rec_col2 = st.columns(2)
            with rec_col1:
                if not st.session_state.is_recording:
                    if st.button("🔴 Start Recording", use_container_width=True):
                        recorder = LiveRecorder()
                        recorder.start()
                        st.session_state.recorder = recorder
                        st.session_state.is_recording = True
                        st.session_state.recorded_file = None
                        st.rerun()
                else:
                    st.error("🔴 Recording...")
                    duration = st.session_state.recorder.get_duration() if st.session_state.recorder else 0
                    st.caption(f"⏱️ {duration:.0f}s recorded")
            with rec_col2:
                if st.session_state.is_recording:
                    if st.button("⏹️ Stop", use_container_width=True, type="primary"):
                        if st.session_state.recorder:
                            file_path = st.session_state.recorder.stop()
                            st.session_state.recorded_file = file_path
                            st.session_state.is_recording = False
                            st.session_state.recording_duration = st.session_state.recorder.get_duration()
                            st.session_state.recorder = None
                            st.rerun()
            if st.session_state.recorded_file:
                duration = st.session_state.recording_duration
                st.success(f"✅ Recording ready! ({duration:.0f}s)")
                if st.button("🗑️ Discard", use_container_width=True):
                    if os.path.exists(st.session_state.recorded_file):
                        os.unlink(st.session_state.recorded_file)
                    st.session_state.recorded_file = None
                    st.session_state.recording_duration = 0
                    st.rerun()
        else:
            st.info("🎤 No microphone detected")

        st.subheader("✍️ Or Paste Transcript")
        manual_text = st.text_area("Paste transcript:", height=150, placeholder="Paste here or import from Google Meet via Integration page...", value=st.session_state.transcript if st.session_state.transcript and not st.session_state.analysis else "")

        st.subheader("🎯 Or Use a Template")
        selected_template = st.selectbox("Template:", list(TEMPLATES.keys()), key="template_selector")
        if selected_template != "None":
            if st.button("📋 Load Template", use_container_width=True):
                st.session_state.selected_template = TEMPLATES[selected_template]
                st.rerun()
        if st.session_state.selected_template:
            st.success("✅ Template loaded!")
            if st.button("❌ Clear", use_container_width=True):
                st.session_state.selected_template = None
                st.rerun()

        analyze_btn = st.button("🚀 Analyze Meeting", type="primary", use_container_width=True)

    with col2:
        st.subheader("ℹ️ 16 AI Agents")
        st.markdown("1. 🎙️ Transcription\n2. 🌍 Language Detection\n3. 🔄 Translation\n4. 🧠 Analysis\n5. 💬 Sentiment\n6. 📊 Productivity\n7. 🎙️ Speaker Analytics\n8. 🔔 Smart Alerts\n9. ⏱️ Cost Calculator\n10. 📊 Competitor Intel\n11. 🧠 Memory\n12. 🔍 Research\n13. 📧 Email Drafter\n14. 🎯 Action Assigner\n15. 📧 Email Personalizer\n16. 🔮 Next Predictor")
        st.subheader("🔗 Google Integration")
        g_status = "🟢 Connected" if google_connected else "🔴 Not connected"
        st.markdown(f"Google Calendar and Meet: **{g_status}**")
        st.caption("Go to 📅 Google Integration to connect")

    st.divider()

    if analyze_btn:
        transcript = ""
        if st.session_state.recorded_file:
            progress = st.progress(0, text="🎙️ Processing recording...")
            try:
                progress.progress(20, text="🎙️ Transcribing...")
                transcript = transcribe_audio(st.session_state.recorded_file)
                if os.path.exists(st.session_state.recorded_file):
                    os.unlink(st.session_state.recorded_file)
                st.session_state.recorded_file = None
                st.session_state.recording_duration = 0
                progress.progress(40, text="✅ Transcribed!")
                with st.expander("View transcript"):
                    st.write(transcript)
            except Exception as e:
                st.error(f"Recording error: {e}")
                st.stop()
        elif uploaded_file:
            progress = st.progress(0, text="🎙️ Starting transcription...")
            try:
                file_path = save_uploaded_file(uploaded_file)
                progress.progress(20, text="🎙️ Transcribing with Whisper...")
                transcript = transcribe_audio(file_path)
                os.unlink(file_path)
                progress.progress(40, text="✅ Done!")
                with st.expander("View transcript"):
                    st.write(transcript)
            except Exception as e:
                st.error(f"Transcription error: {e}")
                st.stop()
        elif st.session_state.selected_template:
            transcript = st.session_state.selected_template
            st.session_state.selected_template = None
            progress = st.progress(40, text="✅ Template loaded!")
        elif manual_text.strip():
            transcript = manual_text.strip()
            progress = st.progress(40, text="✅ Ready!")
        elif st.session_state.transcript:
            transcript = st.session_state.transcript
            progress = st.progress(40, text="✅ Using imported transcript!")
        else:
            st.warning("⚠️ Please provide a transcript.")
            st.stop()

        try:
            st.markdown("### ⚡ Live Agent Pipeline")
            agent_container = st.empty()

            def update_agent_display(current_idx):
                with agent_container.container():
                    cols = st.columns(4)
                    for i, (emoji, name, desc) in enumerate(AGENTS_LIST):
                        col = cols[i % 4]
                        if i < current_idx:
                            col.success(f"{emoji} {name} ✅")
                        elif i == current_idx:
                            col.warning(f"{emoji} **{name}** ⏳")
                        else:
                            col.info(f"{emoji} {name}")

            update_agent_display(0)
            progress.progress(50, text="🤖 Running all 16 agents...")

            analysis_result = [None]
            error_result = [None]

            def run_agents():
                try:
                    analysis_result[0] = orchestrator_agent(transcript)
                except Exception as e:
                    error_result[0] = e

            thread = threading.Thread(target=run_agents)
            thread.start()
            agent_idx = 0
            while thread.is_alive():
                update_agent_display(agent_idx % len(AGENTS_LIST))
                time.sleep(4)
                agent_idx += 1
            thread.join()

            if error_result[0]:
                raise error_result[0]

            analysis = analysis_result[0]
            update_agent_display(len(AGENTS_LIST))
            progress.progress(100, text="✅ All 16 agents completed!")
            save_meeting_to_history(analysis, transcript)
            st.session_state.analysis = analysis
            st.session_state.report = format_report(analysis)
            st.session_state.transcript = transcript
            st.session_state.qa_history = []
            st.session_state.checkboxes = {item: False for item in analysis.get("action_items", [])}
            st.success("✅ Analysis complete!")
        except Exception as e:
            st.error(f"Agent error: {e}")
            st.stop()

    if st.session_state.analysis:
        analysis = st.session_state.analysis
        sentiment = analysis.get("sentiment", {})
        productivity = analysis.get("productivity", {})
        speaker_analytics = analysis.get("speaker_analytics", {})
        alerts = analysis.get("alerts", {})
        cost = analysis.get("cost", {})
        score = sentiment.get("score", 5)
        prod_score = productivity.get("overall_score", 50)
        grade = productivity.get("grade", "C")

        st.subheader("📊 Results")
        lang_info = analysis.get("language_info", {})
        if lang_info and not lang_info.get("is_english", True):
            st.info(f"🌍 Detected: **{lang_info['language']}** — translated to English")
        else:
            st.success("🌍 Language: English")

        if analysis.get("notion_url"):
            st.success(f"📋 Saved to Notion! 👉 [Open Report]({analysis.get('notion_url')})")
        else:
            st.warning("⚠️ Notion sync failed")

        if analysis.get("task_results", {}).get("created", 0) > 0:
            task_urls = analysis.get("task_results", {}).get("task_urls", [])
            if task_urls:
                st.success(f"🎯 {analysis['task_results']['created']} tasks! 👉 [Open]({task_urls[0]})")

        if alerts:
            health = alerts.get("meeting_health", "Good")
            health_emoji = {"Excellent": "🟢", "Good": "🔵", "Fair": "🟡", "Poor": "🔴"}.get(health, "🔵")
            st.info(f"{health_emoji} **Health: {health}** | 📋 {alerts.get('meeting_type', '')} | 💰 ${cost.get('total_cost_usd', 0):.0f}")
            for alert in alerts.get("alerts", []):
                st.warning(f"🔔 {alert}")

        competitor_intel = analysis.get("competitor_intel", {})
        if competitor_intel and competitor_intel.get("competitors_found"):
            st.warning(f"📊 {len(competitor_intel.get('competitors', []))} competitor(s) mentioned!")

        prediction = analysis.get("next_meeting_prediction", {})
        if prediction:
            st.info(f"🔮 **Next:** {prediction.get('meeting_type_suggestion', '')} | ⏱️ {prediction.get('suggested_duration', '')} | 🎯 {prediction.get('confidence_score', 7)}/10")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Decisions", len(analysis.get("decisions", [])))
        m2.metric("Action Items", len(analysis.get("action_items", [])))
        m3.metric("Speakers", len(analysis.get("speakers", [])))
        m4.metric("Sentiment", f"{score}/10")
        m5.metric("Productivity", f"{prod_score}/100 ({grade})")
        st.divider()

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs([
            "📝 Summary", "👥 Speakers", "🎙️ Talk Time", "📊 Productivity", "🔔 Alerts", "⏱️ Cost",
            "💬 Sentiment", "💬 Word Cloud", "🔍 Research & Email", "📧 Personal Emails",
            "🧠 Ask AI", "📊 Competitors", "🧠 Memory", "🔮 Next Meeting"
        ])

        with tab1:
            st.markdown(f"### Summary\n{analysis.get('summary', 'N/A')}")
            st.markdown("### Key Decisions")
            for d in analysis.get("decisions", []):
                st.markdown(f"✅ {d}")
            st.markdown("### 🎯 Action Items")
            assigned_actions = analysis.get("assigned_actions", [])
            if assigned_actions:
                priority_filter = st.selectbox("Filter:", ["All", "High", "Medium", "Low"], key="priority_filter")
                owners = list(set([a["owner"] for a in assigned_actions]))
                for owner in sorted(owners):
                    owner_actions = [a for a in assigned_actions if a["owner"] == owner and (priority_filter == "All" or a["priority"] == priority_filter)]
                    if not owner_actions:
                        continue
                    st.markdown(f"#### 👤 {owner}")
                    for a in owner_actions:
                        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(a["priority"], "⚪")
                        checked = st.session_state.checkboxes.get(a["action"], False)
                        col_check, col_info = st.columns([3, 2])
                        with col_check:
                            new_val = st.checkbox(a["action"], value=checked, key=f"chk_assigned_{hash(a['action'])}")
                            st.session_state.checkboxes[a["action"]] = new_val
                        with col_info:
                            st.caption(f"{priority_emoji} {a['priority']} | ⏰ {a['due']} | 📁 {a['category']}")
            else:
                for idx, item in enumerate(analysis.get("action_items", [])):
                    checked = st.session_state.checkboxes.get(item, False)
                    new_val = st.checkbox(item, value=checked, key=f"chk_item_{idx}_{hash(item)}")
                    st.session_state.checkboxes[item] = new_val
            total = len(st.session_state.checkboxes)
            done = sum(st.session_state.checkboxes.values())
            if total > 0:
                st.progress(done / total, text=f"{done}/{total} completed")
            if analysis.get("risks"):
                st.markdown("### ⚠️ Risks")
                for r in analysis.get("risks", []):
                    st.warning(r)

        with tab2:
            st.markdown("### 👥 Speakers")
            for speaker in analysis.get("speakers", []):
                st.info(f"🗣️ {speaker}")

        with tab3:
            st.markdown("### 🎙️ Talk Time")
            if speaker_analytics and speaker_analytics.get("speakers"):
                speakers_data = speaker_analytics["speakers"]
                names = [s["name"] for s in speakers_data]
                percents = [s["percent"] for s in speakers_data]
                colors = px.colors.qualitative.Set3[:len(names)]
                fig = go.Figure(go.Bar(x=percents, y=names, orientation="h", marker_color=colors, text=[f"{p}%" for p in percents], textposition="outside"))
                fig.update_layout(height=350, margin=dict(l=20, r=60, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis=dict(range=[0, 60]))
                st.plotly_chart(fig, use_container_width=True)
                for s in speakers_data:
                    style_emoji = {"Dominant": "🔴", "Balanced": "🟢", "Reserved": "🔵"}.get(s["style"], "⚪")
                    st.markdown(f"{style_emoji} **{s['name']}** — {s['style']} ({s['percent']}% · ~{s['words']} words)")
                c1, c2, c3 = st.columns(3)
                c1.metric("Most Vocal", speaker_analytics.get("most_vocal", "N/A"))
                c2.metric("Least Vocal", speaker_analytics.get("least_vocal", "N/A"))
                c3.metric("Balance", f"{speaker_analytics.get('balance_score', 5)}/10")
                if speaker_analytics.get("insight"):
                    st.info(f"💡 {speaker_analytics['insight']}")
            else:
                st.info("Not available")

        with tab4:
            st.markdown("### 📊 Productivity")
            grade_emoji = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}.get(grade, "🟡")
            gc1, gc2, gc3 = st.columns(3)
            gc1.metric("Score", f"{prod_score}/100")
            gc2.metric("Grade", f"{grade_emoji} {grade}")
            gc3.metric("Efficiency", f"{productivity.get('time_efficiency', 5)}/10")
            categories = ["Clarity", "Focus", "Decisions", "Time Efficiency", "Participation", "Next Steps"]
            values = [productivity.get("clarity", 5), productivity.get("focus", 5), productivity.get("decisions", 5), productivity.get("time_efficiency", 5), productivity.get("participation", 5), productivity.get("next_steps", 5)]
            values_closed = values + [values[0]]
            categories_closed = categories + [categories[0]]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=values_closed, theta=categories_closed, fill="toself", fillcolor="rgba(99,110,250,0.2)", line=dict(color="rgba(99,110,250,0.8)", width=2), name="Score"))
            fig.add_trace(go.Scatterpolar(r=[10]*7, theta=categories_closed, fill="toself", fillcolor="rgba(200,200,200,0.05)", line=dict(color="rgba(200,200,200,0.3)", width=1, dash="dot"), name="Perfect"))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
            for cat, val in zip(categories, values):
                st.write(f"**{cat}**: {val}/10")
                st.progress(val / 10)
            col_s, col_w = st.columns(2)
            with col_s:
                st.success(f"💪 {productivity.get('biggest_strength', 'N/A')}")
            with col_w:
                st.warning(f"⚠️ {productivity.get('biggest_weakness', 'N/A')}")
            st.info(f"💡 {productivity.get('coach_tip', 'N/A')}")

        with tab5:
            st.markdown("### 🔔 Alerts")
            if alerts:
                health = alerts.get("meeting_health", "Good")
                health_emoji = {"Excellent": "🟢", "Good": "🔵", "Fair": "🟡", "Poor": "🔴"}.get(health, "🔵")
                a1, a2 = st.columns(2)
                a1.metric("Health", f"{health_emoji} {health}")
                a2.metric("Type", alerts.get("meeting_type", "N/A"))
                for alert in alerts.get("alerts", []):
                    st.warning(f"🔔 {alert}")
                for flag in alerts.get("positive_flags", []):
                    st.success(f"🌟 {flag}")
                checks = [("Decisions Made", alerts.get("had_decisions", False)), ("Action Items", alerts.get("had_action_items", False)), ("On Topic", not alerts.get("went_off_topic", False)), ("Balanced", not alerts.get("too_many_speakers_dominated", False)), ("No Conflicts", not alerts.get("unresolved_conflicts", False))]
                for name, passed in checks:
                    st.markdown(f"{'✅' if passed else '❌'} {name}")
                st.info(f"💡 {alerts.get('health_reason', '')}")

        with tab6:
            st.markdown("### ⏱️ Cost")
            if cost:
                roi_emoji = {"Excellent": "🟢", "Good": "🔵", "Fair": "🟡", "Poor": "🔴"}.get(cost.get("roi_rating", "Good"), "🔵")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", f"${cost.get('total_cost_usd', 0):.0f}")
                c2.metric("Duration", f"{cost.get('estimated_duration_minutes', 0)} mins")
                c3.metric("ROI", f"{roi_emoji} {cost.get('roi_rating', 'N/A')}")
                c4, c5, c6 = st.columns(3)
                c4.metric("Participants", cost.get("participant_count", 0))
                c5.metric("Avg Rate", f"${cost.get('avg_hourly_rate_usd', 0):.0f}/hr")
                c6.metric("Wasted", f"{cost.get('time_wasted_minutes', 0)} mins")
                d_count = len(analysis.get("decisions", [])) or 1
                a_count = len(analysis.get("action_items", [])) or 1
                tc = cost.get("total_cost_usd", 0)
                fig = go.Figure(go.Bar(x=["Total", "Per Decision", "Per Action"], y=[tc, cost.get("cost_per_decision_usd", tc/d_count), cost.get("cost_per_action_item_usd", tc/a_count)], marker_color=["#636EFA", "#EF553B", "#00CC96"], text=[f"${tc:.0f}", f"${cost.get('cost_per_decision_usd', 0):.0f}", f"${cost.get('cost_per_action_item_usd', 0):.0f}"], textposition="outside"))
                fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig, use_container_width=True)
                if cost.get("could_be_email"):
                    st.error("📧 This could have been an email!")
                else:
                    st.success("✅ Meeting justified its cost!")
                st.info(f"💡 {cost.get('roi_reason', '')}")

        with tab7:
            emoji = get_sentiment_emoji(sentiment.get("overall", "Neutral"))
            st.markdown(f"### {emoji} {sentiment.get('overall', 'N/A')}")
            st.progress(score / 10)
            c1, c2 = st.columns(2)
            c1.metric("Energy", sentiment.get("energy", "N/A"))
            c2.metric("Collaboration", sentiment.get("collaboration", "N/A"))
            for moment in sentiment.get("key_moments", []):
                st.markdown(f"• {moment}")
            st.success(sentiment.get("recommendation", "N/A"))

        with tab8:
            st.markdown("### 💬 Word Cloud")
            with st.spinner("Generating..."):
                wc_image = generate_wordcloud(st.session_state.transcript)
            if wc_image:
                st.image(wc_image, use_container_width=True)
                top_words = get_top_words(st.session_state.transcript, 15)
                if top_words:
                    max_count = top_words[0][1]
                    for word, count in top_words:
                        cw, cb = st.columns([1, 4])
                        cw.markdown(f"**{word}**")
                        cb.progress(count / max_count, text=f"{count} mentions")
            else:
                st.info("Not available")

        with tab9:
            st.markdown("### 🔍 Research")
            st.write(analysis.get("research", "N/A"))
            st.divider()
            st.markdown("### 📧 Team Follow-up Email")
            st.text_area("Copy:", value=analysis.get("follow_up_email", ""), height=300, key="email_box")

        with tab10:
            st.markdown("### 📧 Personalized Emails")
            st.caption("Individual emails per speaker with their specific action items")
            personalized_emails = analysis.get("personalized_emails", [])
            if personalized_emails:
                st.success(f"✅ {len(personalized_emails)} personalized emails generated!")
                for email_data in personalized_emails:
                    speaker = email_data.get("speaker", "Unknown")
                    role = email_data.get("role", "")
                    subject = email_data.get("subject", "Follow-up")
                    email_body = email_data.get("email", "")
                    action_count = email_data.get("action_count", 0)
                    with st.expander(f"📧 {speaker} — {role} | {action_count} actions | {subject}"):
                        st.markdown(f"**Subject:** {subject}")
                        st.text_area("Email:", value=email_body, height=250, key=f"email_{hash(speaker)}")
                        st.download_button("⬇️ Download", data=f"Subject: {subject}\n\n{email_body}", file_name=f"email_{speaker.replace(' ', '_').lower()}.txt", mime="text/plain", key=f"dl_{hash(speaker)}")
            else:
                st.info("No personalized emails available")

        with tab11:
            st.markdown("### 🧠 Ask AI")
            suggestions = ["What did we decide?", "Who has most actions?", "Main risks?", "Was this productive?", "What to follow up?"]
            cols = st.columns(len(suggestions))
            for i, suggestion in enumerate(suggestions):
                if cols[i].button(suggestion, key=f"suggest_{i}", use_container_width=True):
                    with st.spinner("Thinking..."):
                        answer = qa_agent(suggestion, st.session_state.transcript, analysis)
                        st.session_state.qa_history.append({"question": suggestion, "answer": answer})
            question = st.text_input("Your question:", key="qa_input")
            if st.button("🧠 Ask", type="primary") and question.strip():
                with st.spinner("Thinking..."):
                    answer = qa_agent(question, st.session_state.transcript, analysis)
                    st.session_state.qa_history.append({"question": question, "answer": answer})
            for qa in reversed(st.session_state.qa_history):
                st.markdown(f"**❓ {qa['question']}**")
                st.info(qa["answer"])
                st.divider()

        with tab12:
            st.markdown("### 📊 Competitors")
            competitor_intel = analysis.get("competitor_intel", {})
            if competitor_intel and competitor_intel.get("competitors_found"):
                for comp in competitor_intel.get("competitors", []):
                    threat_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(comp.get("threat_level", "Medium"), "🟡")
                    with st.expander(f"{threat_emoji} {comp['name']}"):
                        st.markdown(f"**Description:** {comp.get('description', '')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**Strengths:**")
                            for s in comp.get("strengths", []):
                                st.markdown(f"- {s}")
                        with c2:
                            st.markdown("**Weaknesses:**")
                            for w in comp.get("weaknesses", []):
                                st.markdown(f"- {w}")
                        st.success(f"🎯 {comp.get('our_advantage', '')}")
            else:
                st.info("✅ No competitors mentioned")

        with tab13:
            st.markdown("### 🧠 Memory")
            memory = analysis.get("memory", {})
            if memory:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("### 👥 New People")
                    for person in memory.get("new_people", []):
                        st.info(f"🗣️ {person}")
                    st.markdown("### 🔑 Topics")
                    for topic in memory.get("key_topics", []):
                        st.markdown(f"• {topic}")
                with col_b:
                    st.markdown("### ✅ Decisions")
                    for d in memory.get("important_decisions", []):
                        st.markdown(f"✅ {d}")
                    st.markdown("### 🔄 Themes")
                    for theme in memory.get("recurring_themes", []):
                        st.warning(f"🔄 {theme}")
                if memory.get("context_update"):
                    st.success(memory["context_update"])
                full_memory = memory.get("full_memory", {})
                if full_memory.get("people"):
                    st.markdown("### 🗂️ All People")
                    for name, role in full_memory["people"].items():
                        st.markdown(f"👤 **{name}** — {role}")
            else:
                st.info("Memory builds up as you analyze more meetings")

        with tab14:
            st.markdown("### 🔮 Next Meeting")
            prediction = analysis.get("next_meeting_prediction", {})
            if prediction:
                conf = prediction.get("confidence_score", 7)
                p1, p2, p3 = st.columns(3)
                p1.metric("Type", prediction.get("meeting_type_suggestion", "N/A"))
                p2.metric("Duration", prediction.get("suggested_duration", "N/A"))
                p3.metric("Confidence", f"{conf}/10")
                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("### 📋 Predicted Topics")
                    for topic in prediction.get("predicted_topics", []):
                        st.info(f"🔮 {topic}")
                    st.markdown("### ⚠️ Predicted Risks")
                    for risk in prediction.get("predicted_risks", []):
                        st.warning(f"⚠️ {risk}")
                with col_b:
                    st.markdown("### 📅 Agenda")
                    for i, item in enumerate(prediction.get("suggested_agenda", []), 1):
                        st.markdown(f"{i}. {item}")
                    st.markdown("### 🔄 Follow-ups")
                    for item in prediction.get("followup_items", []):
                        st.markdown(f"• {item}")
                st.divider()
                for tip in prediction.get("preparation_tips", []):
                    st.success(f"✅ {tip}")
                agenda_text = f"NEXT MEETING\nType: {prediction.get('meeting_type_suggestion')}\nDuration: {prediction.get('suggested_duration')}\n\nAGENDA:\n" + "\n".join([f"{i+1}. {a}" for i, a in enumerate(prediction.get("suggested_agenda", []))])
                st.download_button("📥 Download Agenda", data=agenda_text, file_name="next_agenda.txt", use_container_width=True)
            else:
                st.info("Run analysis to see prediction")

        st.divider()
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(label="⬇️ Markdown", data=st.session_state.report, file_name="meeting_report.md", mime="text/markdown", use_container_width=True)
        with dl2:
            with st.spinner("📄 Preparing PDF..."):
                pdf_bytes = build_pdf_report(analysis)
            st.download_button(label="📄 PDF", data=pdf_bytes, file_name="meeting_report.pdf", mime="application/pdf", use_container_width=True)

elif page == "🔄 Compare Meetings":
    st.title("🔄 Compare Meetings")
    st.divider()
    history = load_history()
    if len(history) < 2:
        st.warning("⚠️ Need at least 2 meetings.")
    else:
        meeting_options = [f"{m['date']} — {m['productivity_score']}/100" for m in reversed(history)]
        reversed_history = list(reversed(history))
        col1, col2 = st.columns(2)
        with col1:
            m1_idx = st.selectbox("Meeting 1:", range(len(meeting_options)), format_func=lambda x: meeting_options[x], key="m1_select")
        with col2:
            m2_idx = st.selectbox("Meeting 2:", range(len(meeting_options)), format_func=lambda x: meeting_options[x], index=min(1, len(meeting_options)-1), key="m2_select")
        if st.button("🔄 Compare", type="primary", use_container_width=True):
            m1 = reversed_history[m1_idx]
            m2 = reversed_history[m2_idx]
            with st.spinner("Comparing..."):
                comparison = compare_meetings_agent(m1, m2)
                st.session_state.comparison_result = {"comparison": comparison, "m1": m1, "m2": m2}
        if st.session_state.comparison_result:
            comp_data = st.session_state.comparison_result
            m1, m2 = comp_data["m1"], comp_data["m2"]
            comparison = comp_data["comparison"]
            better = comparison.get("better_meeting", "1")
            st.success(f"🏆 Meeting {better} — {comparison.get('better_reason', '')}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Meeting 1")
                a, b, c, d = st.columns(4)
                a.metric("Productivity", f"{m1.get('productivity_score', 0)}/100")
                b.metric("Sentiment", f"{m1.get('sentiment_score', 0)}/10")
                c.metric("Decisions", m1.get("decisions_count", 0))
                d.metric("Actions", m1.get("action_items_count", 0))
            with c2:
                st.markdown("#### Meeting 2")
                a, b, c, d = st.columns(4)
                a.metric("Productivity", f"{m2.get('productivity_score', 0)}/100", delta=m2.get("productivity_score", 0)-m1.get("productivity_score", 0))
                b.metric("Sentiment", f"{m2.get('sentiment_score', 0)}/10", delta=m2.get("sentiment_score", 0)-m1.get("sentiment_score", 0))
                c.metric("Decisions", m2.get("decisions_count", 0), delta=m2.get("decisions_count", 0)-m1.get("decisions_count", 0))
                d.metric("Actions", m2.get("action_items_count", 0), delta=m2.get("action_items_count", 0)-m1.get("action_items_count", 0))
            fig = go.Figure()
            cats = ["Productivity", "Sentiment", "Decisions", "Actions"]
            fig.add_trace(go.Bar(name="M1", x=cats, y=[m1.get("productivity_score", 0)/10, m1.get("sentiment_score", 0), m1.get("decisions_count", 0), m1.get("action_items_count", 0)], marker_color="rgba(99,110,250,0.8)"))
            fig.add_trace(go.Bar(name="M2", x=cats, y=[m2.get("productivity_score", 0)/10, m2.get("sentiment_score", 0), m2.get("decisions_count", 0), m2.get("action_items_count", 0)], marker_color="rgba(239,85,59,0.8)"))
            fig.update_layout(barmode="group", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
            ia, ib = st.columns(2)
            with ia:
                for area in comparison.get("improvement_areas", []):
                    st.warning(f"• {area}")
            with ib:
                for theme in comparison.get("common_themes", []):
                    st.info(f"• {theme}")
            st.success(comparison.get("overall_insight", ""))
            st.info(f"🎯 {comparison.get('recommendation', '')}")

elif page == "📚 Meeting History":
    st.title("📚 Meeting History")
    st.divider()
    history = load_history()
    if not history:
        st.info("No meetings yet.")
    else:
        stats = get_history_stats(history)
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Total", stats.get("total_meetings", 0))
        s2.metric("Avg Productivity", f"{stats.get('avg_productivity', 0)}/100")
        s3.metric("Avg Sentiment", f"{stats.get('avg_sentiment', 0)}/10")
        s4.metric("Decisions", stats.get("total_decisions", 0))
        s5.metric("Actions", stats.get("total_actions", 0))
        st.divider()
        if len(history) > 1:
            dates = [m["date"].split(" at ")[0] for m in history]
            scores = [m["productivity_score"] for m in history]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers", line=dict(color="#636EFA", width=3), marker=dict(size=10)))
            fig.add_hline(y=sum(scores)/len(scores), line_dash="dot", line_color="orange", annotation_text=f"Avg: {round(sum(scores)/len(scores), 1)}")
            fig.update_layout(yaxis_range=[0, 100], height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
        for meeting in reversed(history):
            grade = meeting.get("productivity_grade", "C")
            ge = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}.get(grade, "🟡")
            with st.expander(f"📅 {meeting['date']} — {ge} {meeting['productivity_score']}/100 — 🌍 {meeting['language']}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Productivity", f"{meeting['productivity_score']}/100")
                c2.metric("Sentiment", f"{meeting['sentiment_score']}/10")
                c3.metric("Decisions", meeting["decisions_count"])
                c4.metric("Actions", meeting["action_items_count"])
                st.markdown(f"**Summary:** {meeting['summary']}")
                if meeting.get("notion_url"):
                    st.markdown(f"[📋 Notion]({meeting['notion_url']})")

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    st.divider()
    history = load_history()
    if len(history) < 2:
        st.info("Analyze at least 2 meetings!")
    else:
        sorted_best = sorted(history, key=lambda x: x.get("productivity_score", 0), reverse=True)
        sorted_worst = sorted(history, key=lambda x: x.get("productivity_score", 0))
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Total", len(history))
        t2.metric("🥇 Best", f"{sorted_best[0].get('productivity_score', 0)}/100")
        t3.metric("😬 Worst", f"{sorted_worst[0].get('productivity_score', 0)}/100")
        t4.metric("📈 Avg", f"{round(sum(m.get('productivity_score', 0) for m in history)/len(history), 1)}/100")
        names = [f"#{i+1} {m['date'].split(' at ')[0]}" for i, m in enumerate(sorted_best)]
        scores = [m.get("productivity_score", 0) for m in sorted_best]
        grades = [m.get("productivity_grade", "C") for m in sorted_best]
        colors = ["#00CC96" if s >= 80 else "#636EFA" if s >= 60 else "#FFA15A" if s >= 40 else "#EF553B" for s in scores]
        fig = go.Figure(go.Bar(x=names, y=scores, marker_color=colors, text=[f"{s}/100 ({g})" for s, g in zip(scores, grades)], textposition="outside"))
        fig.update_layout(yaxis_range=[0, 115], height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### 🥇 Top 3")
        medals = ["🥇", "🥈", "🥉"]
        top3 = sorted_best[:min(3, len(sorted_best))]
        cols = st.columns(len(top3))
        for i, (col, m) in enumerate(zip(cols, top3)):
            with col:
                ge = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}.get(m.get("productivity_grade", "C"), "🟡")
                st.markdown(f"### {medals[i]}")
                st.metric("Score", f"{m.get('productivity_score', 0)}/100")
                st.caption(f"{ge} {m.get('productivity_grade', 'C')} | {m['date'].split(' at ')[0]}")

elif page == "📈 Trend Analyzer":
    st.title("📈 Trend Analyzer")
    st.divider()
    history = load_history()
    if len(history) < 2:
        st.info("Analyze at least 2 meetings!")
    else:
        if st.button("🔍 Analyze Trends", type="primary", use_container_width=True):
            with st.spinner("Analyzing..."):
                trends = trend_analyzer_agent(history)
                st.session_state.trends = trends
            st.success("✅ Done!")
        if st.session_state.trends:
            trends = st.session_state.trends
            health = trends.get("overall_health", "Good")
            health_emoji = {"Excellent": "🟢", "Good": "🔵", "Fair": "🟡", "Poor": "🔴"}.get(health, "🔵")
            st.info(f"{health_emoji} **{health}** — {trends.get('health_reason', '')}")
            t1, t2 = st.columns(2)
            te = {"Improving": "📈", "Declining": "📉", "Stable": "➡️", "Fluctuating": "📊"}
            t1.metric("Productivity", f"{te.get(trends.get('productivity_trend', 'Stable'), '➡️')} {trends.get('productivity_trend', 'Stable')}")
            t2.metric("Sentiment", f"{te.get(trends.get('sentiment_trend', 'Stable'), '➡️')} {trends.get('sentiment_trend', 'Stable')}")
            st.divider()
            dates = [m["date"].split(" at ")[0] for m in history]
            prod_scores = [m.get("productivity_score", 0) for m in history]
            sent_scores = [m.get("sentiment_score", 0) * 10 for m in history]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=prod_scores, mode="lines+markers", name="Productivity", line=dict(color="#636EFA", width=3), fill="tozeroy", fillcolor="rgba(99,110,250,0.1)"))
            fig.add_trace(go.Scatter(x=dates, y=sent_scores, mode="lines+markers", name="Sentiment x10", line=dict(color="#00CC96", width=2, dash="dot")))
            if len(prod_scores) > 1:
                z = np.polyfit(range(len(prod_scores)), prod_scores, 1)
                p = np.poly1d(z)
                fig.add_trace(go.Scatter(x=dates, y=[p(i) for i in range(len(prod_scores))], mode="lines", name="Trend", line=dict(color="orange", width=2, dash="dash")))
            fig.update_layout(yaxis_range=[0, 110], height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
            sw1, sw2 = st.columns(2)
            with sw1:
                st.success(f"💪 {trends.get('top_strength', 'N/A')}")
                st.info(trends.get("best_day_pattern", "N/A"))
            with sw2:
                st.warning(f"⚠️ {trends.get('top_weakness', 'N/A')}")
                st.error(trends.get("worst_pattern", "N/A"))
            st.markdown("### 🔍 Patterns")
            for p in trends.get("patterns", []):
                st.info(f"• {p}")
            st.markdown("### 💡 Recommendations")
            for i, r in enumerate(trends.get("recommendations", []), 1):
                st.success(f"{i}. {r}")
            st.markdown("### 🔮 Prediction")
            st.info(f"🔮 {trends.get('prediction', 'N/A')}")
