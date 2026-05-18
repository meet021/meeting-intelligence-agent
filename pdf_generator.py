from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable,
                                 KeepTogether)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import io
from datetime import datetime


# ── Color palette ────────────────────────────────────────────────────
DARK_BG = HexColor('#1a1a2e')
PURPLE = HexColor('#636EFA')
CORAL = HexColor('#EF553B')
GREEN = HexColor('#00CC96')
AMBER = HexColor('#FFA15A')
BLUE = HexColor('#19D3F3')
LIGHT_GRAY = HexColor('#f8f9fa')
DARK_GRAY = HexColor('#343a40')
MID_GRAY = HexColor('#6c757d')
WHITE = HexColor('#ffffff')


def build_pdf_report(analysis: dict) -> bytes:
    """Generate a beautiful PDF report from meeting analysis."""
    print("📄 PDF Generator running...")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Custom styles ────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=PURPLE,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=MID_GRAY,
        spaceAfter=20,
        alignment=TA_CENTER
    )

    heading1_style = ParagraphStyle(
        'Heading1Custom',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=PURPLE,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderPad=4
    )

    heading2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=DARK_GRAY,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_GRAY,
        spaceAfter=6,
        leading=16
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_GRAY,
        spaceAfter=4,
        leftIndent=20,
        leading=15
    )

    small_style = ParagraphStyle(
        'SmallCustom',
        parent=styles['Normal'],
        fontSize=9,
        textColor=MID_GRAY,
        spaceAfter=4
    )

    # ── Helper functions ─────────────────────────────────────────────
    def add_section_header(text, emoji=""):
        story.append(Spacer(1, 8))
        story.append(HRFlowable(
            width="100%",
            thickness=2,
            color=PURPLE,
            spaceAfter=8
        ))
        story.append(Paragraph(f"{emoji} {text}", heading1_style))

    def add_metric_table(metrics: list):
        """metrics = list of (label, value) tuples"""
        cols = min(len(metrics), 4)
        rows = [metrics[i:i+cols] for i in range(0, len(metrics), cols)]

        for row in rows:
            # Pad row if needed
            while len(row) < cols:
                row.append(("", ""))

            table_data = [
                [Paragraph(f"<b>{v}</b>", ParagraphStyle(
                    'MetricVal', fontSize=16, textColor=PURPLE,
                    alignment=TA_CENTER, fontName='Helvetica-Bold'
                )) for _, v in row],
                [Paragraph(l, ParagraphStyle(
                    'MetricLabel', fontSize=8, textColor=MID_GRAY,
                    alignment=TA_CENTER
                )) for l, _ in row]
            ]

            col_width = (doc.width) / cols
            t = Table(table_data, colWidths=[col_width] * cols)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT_GRAY]),
                ('BOX', (0, 0), (-1, -1), 0.5, MID_GRAY),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, MID_GRAY),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('ROUNDEDCORNERS', [4]),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

    # ── TITLE PAGE ───────────────────────────────────────────────────
    today = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    lang = analysis.get("language_info", {}).get("language", "English")
    sentiment = analysis.get("sentiment", {})
    productivity = analysis.get("productivity", {})
    cost = analysis.get("cost", {})
    alerts = analysis.get("alerts", {})

    story.append(Spacer(1, 20))
    story.append(Paragraph("🤖 Meeting Intelligence Report", title_style))
    story.append(Paragraph(f"Generated on {today}", subtitle_style))
    story.append(Paragraph(f"Language: {lang}  |  Meeting Type: {alerts.get('meeting_type', 'N/A')}  |  Health: {alerts.get('meeting_health', 'N/A')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=3, color=PURPLE, spaceAfter=20))

    # ── KEY METRICS ──────────────────────────────────────────────────
    add_section_header("Key Metrics", "📊")
    metrics = [
        ("Decisions Made", str(len(analysis.get("decisions", [])))),
        ("Action Items", str(len(analysis.get("action_items", [])))),
        ("Speakers", str(len(analysis.get("speakers", [])))),
        ("Sentiment Score", f"{sentiment.get('score', 5)}/10"),
        ("Productivity", f"{productivity.get('overall_score', 50)}/100"),
        ("Grade", productivity.get("grade", "C")),
        ("Meeting Cost", f"${cost.get('total_cost_usd', 0):.0f}"),
        ("Duration", f"{cost.get('estimated_duration_minutes', 0)} min"),
    ]
    add_metric_table(metrics)

    # ── SUMMARY ──────────────────────────────────────────────────────
    add_section_header("Meeting Summary", "📝")
    story.append(Paragraph(analysis.get("summary", "No summary available"), body_style))

    # ── SPEAKERS ─────────────────────────────────────────────────────
    if analysis.get("speakers"):
        add_section_header("Speakers", "👥")
        for speaker in analysis["speakers"]:
            story.append(Paragraph(f"🗣️ {speaker}", bullet_style))

    # ── KEY DECISIONS ────────────────────────────────────────────────
    if analysis.get("decisions"):
        add_section_header("Key Decisions", "✅")
        for i, decision in enumerate(analysis["decisions"], 1):
            story.append(Paragraph(f"{i}. {decision}", bullet_style))

    # ── ACTION ITEMS ─────────────────────────────────────────────────
    if analysis.get("action_items"):
        add_section_header("Action Items", "🎯")
        action_data = [["#", "Action Item", "Status"]]
        for i, item in enumerate(analysis["action_items"], 1):
            action_data.append([str(i), item, "⬜ Pending"])

        action_table = Table(
            action_data,
            colWidths=[0.4 * inch, 4.5 * inch, 1.0 * inch]
        )
        action_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, MID_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ]))
        story.append(action_table)

    # ── RISKS ────────────────────────────────────────────────────────
    if analysis.get("risks"):
        add_section_header("Risks & Concerns", "⚠️")
        for risk in analysis["risks"]:
            story.append(Paragraph(f"⚠️ {risk}", bullet_style))

    # ── PRODUCTIVITY SCORE ───────────────────────────────────────────
    add_section_header("Productivity Score", "📊")
    prod_metrics = [
        ("Clarity", f"{productivity.get('clarity', 5)}/10"),
        ("Focus", f"{productivity.get('focus', 5)}/10"),
        ("Decisions", f"{productivity.get('decisions', 5)}/10"),
        ("Time Efficiency", f"{productivity.get('time_efficiency', 5)}/10"),
        ("Participation", f"{productivity.get('participation', 5)}/10"),
        ("Next Steps", f"{productivity.get('next_steps', 5)}/10"),
    ]
    add_metric_table(prod_metrics)

    story.append(Paragraph(
        f"💪 Strength: {productivity.get('biggest_strength', 'N/A')}",
        body_style
    ))
    story.append(Paragraph(
        f"⚠️ Weakness: {productivity.get('biggest_weakness', 'N/A')}",
        body_style
    ))
    story.append(Paragraph(
        f"💡 Coach Tip: {productivity.get('coach_tip', 'N/A')}",
        body_style
    ))

    # ── SENTIMENT ────────────────────────────────────────────────────
    add_section_header("Sentiment Analysis", "💬")
    sent_metrics = [
        ("Overall", sentiment.get("overall", "N/A")),
        ("Score", f"{sentiment.get('score', 5)}/10"),
        ("Energy", sentiment.get("energy", "N/A")),
        ("Collaboration", sentiment.get("collaboration", "N/A")),
    ]
    add_metric_table(sent_metrics)

    if sentiment.get("key_moments"):
        story.append(Paragraph("Key Emotional Moments:", heading2_style))
        for moment in sentiment["key_moments"]:
            story.append(Paragraph(f"• {moment}", bullet_style))

    if sentiment.get("recommendation"):
        story.append(Paragraph(
            f"💡 Recommendation: {sentiment['recommendation']}",
            body_style
        ))

    # ── SMART ALERTS ─────────────────────────────────────────────────
    if alerts:
        add_section_header("Smart Alerts", "🔔")
        if alerts.get("alerts"):
            story.append(Paragraph("Alerts:", heading2_style))
            for alert in alerts["alerts"]:
                story.append(Paragraph(f"🔔 {alert}", bullet_style))
        if alerts.get("positive_flags"):
            story.append(Paragraph("Positive Flags:", heading2_style))
            for flag in alerts["positive_flags"]:
                story.append(Paragraph(f"🌟 {flag}", bullet_style))

    # ── MEETING COST ─────────────────────────────────────────────────
    if cost:
        add_section_header("Meeting Cost Analysis", "⏱️")
        cost_metrics = [
            ("Total Cost", f"${cost.get('total_cost_usd', 0):.0f}"),
            ("Duration", f"{cost.get('estimated_duration_minutes', 0)} min"),
            ("Participants", str(cost.get("participant_count", 0))),
            ("ROI Rating", cost.get("roi_rating", "N/A")),
        ]
        add_metric_table(cost_metrics)
        story.append(Paragraph(
            f"💡 {cost.get('roi_reason', 'N/A')}",
            body_style
        ))

    # ── RESEARCH ─────────────────────────────────────────────────────
    if analysis.get("research"):
        add_section_header("Research & Context", "🔍")
        story.append(Paragraph(analysis["research"], body_style))

    # ── FOLLOW-UP EMAIL ──────────────────────────────────────────────
    if analysis.get("follow_up_email"):
        add_section_header("Follow-up Email Draft", "📧")
        email_style = ParagraphStyle(
            'EmailStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=DARK_GRAY,
            backColor=LIGHT_GRAY,
            borderPad=10,
            leading=14,
            leftIndent=10,
            rightIndent=10,
            spaceAfter=6
        )
        for line in analysis["follow_up_email"].split('\n'):
            if line.strip():
                story.append(Paragraph(line, email_style))
            else:
                story.append(Spacer(1, 4))

    # ── FOOTER ───────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))
    story.append(Paragraph(
        "Generated by Meeting Intelligence Agent | Powered by Claude Sonnet (Anthropic)",
        ParagraphStyle('Footer', parent=styles['Normal'],
                       fontSize=8, textColor=MID_GRAY, alignment=TA_CENTER)
    ))

    # ── Build PDF ────────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()