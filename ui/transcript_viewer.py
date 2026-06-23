"""
Transcript Viewer Component — Shows the extracted text from a video
with timestamps. Central to the "Video → Text → Query" value prop.
"""

import os
import json


def load_transcript_for_course(course_id: str, library) -> str:
    """Load the transcript JSON for a course and return styled HTML."""
    if not course_id:
        return _empty_state()

    try:
        course = library.get_course(course_id)
    except Exception:
        return _empty_state()

    # Locate the transcript file
    course_dir = os.path.dirname(course.original_video_path)
    transcript_path = os.path.join(course_dir, "transcript.json")

    if not os.path.exists(transcript_path):
        status = course.transcript_status
        if status == "pending" or status == "processing":
            return _processing_state()
        return _no_transcript_state()

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _error_state()

    chunks = data.get("chunks", [])
    if not chunks:
        return _no_transcript_state()

    return _build_transcript_html(chunks)


def _empty_state() -> str:
    return """
    <div class="tv-empty">
        <div class="tv-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                <path d="M15.6 11.6L14 10v6l1.6-1.6M22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10Z"/>
                <path d="M14 10l-3.5-2v8l3.5-2"/>
            </svg>
        </div>
        <p class="tv-empty-title">No Course Selected</p>
        <p class="tv-empty-sub">Select a course from the sidebar to view its transcript</p>
    </div>
    """


def _processing_state() -> str:
    return """
    <div class="tv-empty">
        <div class="tv-processing-spinner"></div>
        <p class="tv-empty-title">Transcribing...</p>
        <p class="tv-empty-sub">AI is extracting text from your video. This may take a few minutes.<br>Refresh the page shortly.</p>
    </div>
    """


def _no_transcript_state() -> str:
    return """
    <div class="tv-empty">
        <div class="tv-empty-icon" style="opacity:0.4">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/>
                <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
            </svg>
        </div>
        <p class="tv-empty-title">No Transcript Yet</p>
        <p class="tv-empty-sub">The transcript will appear here once processing is complete.</p>
    </div>
    """


def _error_state() -> str:
    return """
    <div class="tv-empty">
        <p class="tv-empty-title" style="color:var(--color-error)">Failed to Load Transcript</p>
        <p class="tv-empty-sub">There was an error reading the transcript file.</p>
    </div>
    """


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    total_sec = int(seconds)
    mins, secs = divmod(total_sec, 60)
    return f"{mins:02d}:{secs:02d}"


def _build_transcript_html(chunks: list) -> str:
    """Build a beautiful scrollable transcript from chunk data."""
    # Header stats
    total_segments = len(chunks)
    total_words = sum(len(c.get("text", "").split()) for c in chunks)

    if chunks:
        last_end = max(c.get("end", 0) for c in chunks)
        duration_str = _format_timestamp(last_end)
    else:
        duration_str = "00:00"

    html = f"""
    <div class="tv-container">
        <div class="tv-header">
            <div class="tv-header-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/>
                    <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
                </svg>
                <span>Extracted Transcript</span>
            </div>
            <div class="tv-stats">
                <span class="tv-stat-chip">{total_segments} segments</span>
                <span class="tv-stat-chip">{total_words:,} words</span>
                <span class="tv-stat-chip">{duration_str} duration</span>
            </div>
        </div>
        <div class="tv-segments">
    """

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue
        start = chunk.get("start", 0)
        ts = _format_timestamp(start)
        seconds = int(start)

        html += f"""
        <div class="tv-segment" onclick="seekVideo({seconds})">
            <span class="tv-timestamp">{ts}</span>
            <span class="tv-text">{text}</span>
        </div>
        """

    html += """
        </div>
    </div>
    <script>
    function seekVideo(seconds) {
        var videos = document.querySelectorAll('video');
        if(videos.length > 0) {
            videos[0].currentTime = seconds;
            videos[0].play();
        }
    }
    </script>
    """
    return html
