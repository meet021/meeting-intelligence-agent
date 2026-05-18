import os
from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

notion = Client(auth=os.getenv("NOTION_API_KEY"))
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")


def create_meeting_report_in_notion(analysis: dict) -> str:
    """Create a full meeting report page in Notion and return the URL."""
    print("📋 Notion Integration Agent running...")

    try:
        today = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        lang = analysis.get("language_info", {}).get("language", "English")
        sentiment = analysis.get("sentiment", {})
        productivity = analysis.get("productivity", {})

        children = []

        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {
                    "content": "🤖 Meeting Intelligence Report"
                }}]
            }
        })

        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {
                    "content": f"📅 {today}  |  🌍 Language: {lang}"
                }}]
            }
        })

        children.append({"object": "block", "type": "divider", "divider": {}})

        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📝 Summary"}}]
            }
        })
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {
                    "content": analysis.get("summary", "No summary available")
                }}]
            }
        })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if analysis.get("speakers"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "👥 Speakers"}}]
                }
            })
            for speaker in analysis["speakers"]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": speaker}}]
                    }
                })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if analysis.get("decisions"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "✅ Key Decisions"}}]
                }
            })
            for decision in analysis["decisions"]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": decision}}]
                    }
                })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if analysis.get("action_items"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🎯 Action Items"}}]
                }
            })
            for item in analysis["action_items"]:
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": item}}],
                        "checked": False
                    }
                })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if productivity:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📊 Productivity Score"}}]
                }
            })
            score_text = (
                f"Overall: {productivity.get('overall_score', 'N/A')}/100  |  "
                f"Grade: {productivity.get('grade', 'N/A')}  |  "
                f"Clarity: {productivity.get('clarity', 'N/A')}/10  |  "
                f"Focus: {productivity.get('focus', 'N/A')}/10"
            )
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": score_text}}]
                }
            })
            if productivity.get("coach_tip"):
                children.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {
                            "content": f"💡 Coach Tip: {productivity['coach_tip']}"
                        }}],
                        "icon": {"emoji": "💡"}
                    }
                })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if sentiment:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "💬 Sentiment Analysis"}}]
                }
            })
            sentiment_text = (
                f"Overall: {sentiment.get('overall', 'N/A')}  |  "
                f"Score: {sentiment.get('score', 'N/A')}/10  |  "
                f"Energy: {sentiment.get('energy', 'N/A')}  |  "
                f"Collaboration: {sentiment.get('collaboration', 'N/A')}"
            )
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": sentiment_text}}]
                }
            })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if analysis.get("risks"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "⚠️ Risks & Concerns"}}]
                }
            })
            for risk in analysis["risks"]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": risk}}]
                    }
                })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if analysis.get("research"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🔍 Research & Context"}}]
                }
            })
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {
                        "content": analysis.get("research", "")
                    }}]
                }
            })

        children.append({"object": "block", "type": "divider", "divider": {}})

        if analysis.get("follow_up_email"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📧 Follow-up Email Draft"}}]
                }
            })
            children.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {
                        "content": analysis.get("follow_up_email", "")
                    }}],
                    "language": "plain text"
                }
            })

        response = notion.pages.create(
            parent={"type": "page_id", "page_id": NOTION_PAGE_ID},
            properties={
                "title": {
                    "title": [{"text": {"content": f"📋 Meeting Report — {today}"}}]
                }
            },
            children=children
        )

        page_url = response.get("url", "")
        print(f"✅ Notion page created: {page_url}")
        return page_url

    except Exception as e:
        print(f"❌ Notion error: {e}")
        import traceback
        traceback.print_exc()
        return ""


def create_tasks_in_notion(action_items: list, meeting_summary: str) -> dict:
    """Create individual task pages in Notion for each action item."""
    print("🎯 Auto Task Creator running...")

    results = {
        "created": 0,
        "failed": 0,
        "task_urls": []
    }

    try:
        today = datetime.now().strftime("%B %d, %Y")

        tasks_page = notion.pages.create(
            parent={"type": "page_id", "page_id": NOTION_PAGE_ID},
            properties={
                "title": {
                    "title": [{"text": {"content": f"🎯 Action Items — {today}"}}]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {
                            "content": f"🎯 Action Items from Meeting — {today}"
                        }}]
                    }
                },
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {
                            "content": f"Meeting Context: {meeting_summary[:300]}"
                        }}],
                        "icon": {"emoji": "📋"}
                    }
                },
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {
                            "content": "📋 Tasks"
                        }}]
                    }
                }
            ] + [
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": item}}],
                        "checked": False
                    }
                }
                for item in action_items
            ]
        )

        results["created"] = len(action_items)
        results["task_urls"].append(tasks_page.get("url", ""))
        print(f"✅ Created {len(action_items)} tasks in Notion!")

    except Exception as e:
        print(f"❌ Task creation error: {e}")
        results["failed"] = len(action_items)

    return results