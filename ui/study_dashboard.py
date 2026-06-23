import gradio as gr
from processors.analytics_tracker import AnalyticsTracker


def _metric_card(icon_svg: str, label: str, value: str, color: str) -> str:
    return f"""
    <div class="dash-card">
        <div class="dash-card-icon" style="background: {color}15; color: {color}">
            {icon_svg}
        </div>
        <div class="dash-card-info">
            <span class="dash-card-value">{value}</span>
            <span class="dash-card-label">{label}</span>
        </div>
    </div>
    """


def _build_dashboard_html(a) -> str:
    """Build a fully styled dashboard from analytics data."""

    # ── Metric cards ──
    icon_q = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
    icon_c = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
    icon_f = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>'
    icon_d = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'

    last_date = a.last_accessed[:10] if a.last_accessed else "Never"

    metrics_html = f"""
    <div class="dash-metrics">
        {_metric_card(icon_q, "Questions Asked", str(a.questions_asked), "#6366F1")}
        {_metric_card(icon_c, "Concepts Explored", str(len(a.concepts_learned)), "#8B5CF6")}
        {_metric_card(icon_d, "Last Accessed", last_date, "#10B981")}
    </div>
    """

    # ── Topic frequency bars ──
    bars_html = ""
    if a.most_asked_topics:
        sorted_topics = sorted(a.most_asked_topics.items(), key=lambda x: x[1], reverse=True)[:8]
        max_val = sorted_topics[0][1] if sorted_topics else 1
        for topic, count in sorted_topics:
            pct = min(int((count / max_val) * 100), 100)
            bars_html += f"""
            <div class="dash-bar-row">
                <span class="dash-bar-label">{topic}</span>
                <div class="dash-bar-track">
                    <div class="dash-bar-fill" style="width:{pct}%"></div>
                </div>
                <span class="dash-bar-count">{count}</span>
            </div>
            """
    else:
        bars_html = '<p class="dash-empty-hint">Ask questions in the AI Tutor tab to populate topic data.</p>'

    # ── Focus / strong areas ──
    weak_items = "".join(f'<span class="dash-tag dash-tag-weak">{w}</span>' for w in a.weak_areas) if a.weak_areas else '<span class="dash-empty-hint">No data yet</span>'
    strong_items = "".join(f'<span class="dash-tag dash-tag-strong">{s}</span>' for s in a.strong_areas) if a.strong_areas else '<span class="dash-empty-hint">No data yet</span>'

    # ── Recent activity ──
    activity_html = ""
    if a.recent_activity:
        for r in a.recent_activity[-8:]:
            activity_html += f'<div class="dash-activity-item">{r}</div>'
    else:
        activity_html = '<p class="dash-empty-hint">No activity recorded yet.</p>'

    return f"""
    <div class="dash-container">
        {metrics_html}

        <div class="dash-grid-2">
            <div class="dash-section">
                <h3 class="dash-section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
                    Topic Frequency
                </h3>
                <div class="dash-bars">{bars_html}</div>
            </div>

            <div class="dash-section">
                <h3 class="dash-section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    Learning Areas
                </h3>
                <div style="margin-bottom:12px">
                    <p class="dash-area-label">Focus Areas (Most Questioned)</p>
                    <div class="dash-tags">{weak_items}</div>
                </div>
                <div>
                    <p class="dash-area-label">Strong Areas</p>
                    <div class="dash-tags">{strong_items}</div>
                </div>
            </div>
        </div>

        <div class="dash-section">
            <h3 class="dash-section-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                Recent Activity
            </h3>
            <div class="dash-activity">{activity_html}</div>
        </div>
    </div>
    """


def render_dashboard(tracker: AnalyticsTracker):
    """Renders the Analytics Dashboard UI components and returns their references."""

    def fetch_data(course_id):
        if not course_id:
            return """
            <div class="dash-container">
                <div class="dash-empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48" style="opacity:0.3">
                        <path d="M18 20V10M12 20V4M6 20v-6"/>
                    </svg>
                    <p style="font-size:15px;font-weight:500;color:var(--color-text-2);margin:12px 0 4px">Select a Course</p>
                    <p style="font-size:13px;color:var(--color-text-3)">Choose a course from the sidebar to view your learning analytics.</p>
                </div>
            </div>
            """

        a = tracker.storage.get_analytics(course_id)
        return _build_dashboard_html(a)

    with gr.Column():
        dashboard_html = gr.HTML(
            value='<div class="dash-container"><div class="dash-empty-state"><p style="font-size:14px;color:var(--color-text-3)">Select a course to view analytics.</p></div></div>',
            elem_id="ll-dashboard"
        )

        refresh_btn = gr.Button("↻ Refresh Dashboard", size="sm")

        outputs = [dashboard_html]
        return outputs, fetch_data, refresh_btn
