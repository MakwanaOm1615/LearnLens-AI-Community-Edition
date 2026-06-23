"""
LearnLens AI — Content to Text to Query
Version 3 (Professional Light Theme)

Architecture:
  Layer 1 — Python backend (untouched)
  Layer 2 — Gradio components with premium CSS theming
  Layer 3 — Custom HTML sections

Author: Om Makwana
"""

import gradio as gr
import os
import logging
import threading
from dotenv import load_dotenv

# ── Providers ──────────────────────────────────────────────────────────
from providers.embedding_provider import BAAIEmbeddingProvider
from providers.vector_store_provider import ChromaDBProvider
from providers.llm_provider import GeminiLLMProvider, OllamaLLMProvider

# ── Storage & Processors ──────────────────────────────────────────────
from storage.course_library import CourseLibrary
from storage.analytics_storage import AnalyticsStorage
from processors.content_ingestion import ContentIngestionProcessor
from processors.transcript_generator import TranscriptGenerator
from processors.chunker import TranscriptChunker
from processors.retriever import CourseRetriever
from processors.generator import AnswerGenerator
from processors.ai_tools import AITools
from processors.analytics_tracker import AnalyticsTracker

# ── UI Components ─────────────────────────────────────────────────────
from ui.study_dashboard import render_dashboard
from ui.timeline_components import build_timeline_html
from ui.transcript_viewer import load_transcript_for_course

# ── Configuration ─────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Global State ──────────────────────────────────────────────────────
embedding_provider = BAAIEmbeddingProvider()
vector_store = ChromaDBProvider(embedding_provider)

if os.getenv("GOOGLE_API_KEY"):
    llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"))
    MODEL_DISPLAY_NAME = "Gemini"
else:
    llm_provider = OllamaLLMProvider(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model_name="llama3.2",
    )
    MODEL_DISPLAY_NAME = "Llama 3.2"

library = CourseLibrary()
analytics_storage = AnalyticsStorage()
analytics_tracker = AnalyticsTracker(analytics_storage)

ingestion = ContentIngestionProcessor()
transcriber = TranscriptGenerator()
chunker = TranscriptChunker()
retriever = CourseRetriever(vector_store)
generator = AnswerGenerator(llm_provider, retriever)
ai_tools = AITools(llm_provider, retriever)


# ═══════════════════════════════════════════════════════════════════════
# BACKEND FUNCTIONS (UNTOUCHED)
# ═══════════════════════════════════════════════════════════════════════

def update_library_view():
    """Return updated dropdown choices, a library HTML summary, and checkboxes."""
    courses = library.get_all_courses()
    if not courses:
        return [
            gr.update(choices=[], value=None),
            "<p class='ll-empty-lib'>No content uploaded yet.</p>",
            gr.update(choices=[], value=[])
        ]

    choices = [(c.title, c.course_id) for c in courses]
    
    checkbox_choices = []
    for c in courses:
        if c.embedding_status == "completed":
            status_text = "Ready"
        elif c.embedding_status == "failed":
            status_text = "Failed"
        else:
            status_text = "Processing"
        checkbox_choices.append((f"{c.title} ({status_text})", c.course_id))

    html = ""
    for c in courses:
        if c.embedding_status == "completed":
            status_cls = "ll-status-ok"
            status_label = "Ready"
        elif c.embedding_status == "failed":
            status_cls = "ll-status-error"
            status_label = "Failed"
        else:
            status_cls = "ll-status-pending"
            status_label = "Processing"

        html += f"""<div class='ll-lib-item'>
            <div class='ll-lib-icon'>
                <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' width='15' height='15'>
                    <path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z'/>
                    <path d='M14 2v6h6'/>
                </svg>
            </div>
            <div class='ll-lib-info'>
                <span class='ll-lib-name'>{c.title}</span>
                <span class='ll-lib-status {status_cls}'>{status_label}</span>
            </div>
        </div>"""
    return [
        gr.update(choices=choices, value=choices[-1][1] if choices else None),
        html,
        gr.update(choices=checkbox_choices, value=[])
    ]



def process_video_background(course):
    """Background thread: transcribe -> chunk -> embed."""
    try:
        transcript = transcriber.process_course(course)
        library.save_course(course)

        course.embedding_status = "processing"
        library.save_course(course)

        docs = chunker.chunk_transcript(transcript)
        vector_store.add_documents(course.course_id, docs)

        course.embedding_status = "completed"
        course.num_chunks = len(docs)
        library.save_course(course)
    except Exception as e:
        course.transcript_status = f"failed: {e}"
        course.embedding_status = "failed"
        library.save_course(course)


def handle_upload(video_file, video_url, title):
    """Handle file upload or URL ingestion."""
    if not video_file and not video_url:
        gr.Warning("No file or URL provided.")
        return "Error: No content provided.", *update_library_view()

    gr.Info("Received content. Starting ingestion...")

    try:
        if video_url and video_url.strip():
            course = ingestion.ingest_url(video_url.strip(), title)
        else:
            course = ingestion.ingest_content(video_file.name, title)
    except Exception as e:
        gr.Error(f"Ingestion failed: {str(e)}")
        return f"Error: {str(e)}", *update_library_view()
    library.save_course(course)

    threading.Thread(target=process_video_background, args=(course,)).start()

    gr.Info("Background processing started. Check the library shortly.")
    msg = f"Uploaded '{course.title}'. Processing in background — refresh the library in a moment."
    return msg, *update_library_view()


def get_summary(course_id: str):
    """Generate chapter summary for a course."""
    if not course_id:
        return gr.update(value="Select a course first.", visible=True)
    result = ai_tools.generate_summary(course_id)
    return gr.update(value=result, visible=True)


def load_video_for_course(course_id: str):
    """Load video path for the selected course. Hide player if no video."""
    if not course_id:
        return gr.update(value=None), gr.update(visible=False)
    try:
        course = library.get_course(course_id)
        video_path = course.original_video_path
        if video_path and os.path.exists(video_path):
            ext = os.path.splitext(video_path)[1].lower()
            if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                return gr.update(value=video_path), gr.update(visible=True)
        return gr.update(value=None), gr.update(visible=False)
    except Exception:
        return gr.update(value=None), gr.update(visible=False)


def load_transcript_view(course_id: str) -> str:
    """Load the transcript viewer HTML for the selected course."""
    return load_transcript_for_course(course_id, library)


def handle_delete(selected_ids: list):
    """Delete selected contents from the library, filesystem, and vector database."""
    if not selected_ids:
        gr.Warning("No files selected to delete. Check the boxes next to the files you want to delete.")
        return update_library_view()
    try:
        deleted_count = 0
        for course_id in selected_ids:
            vector_store.delete_collection(course_id)
            library.delete_course(course_id)
            deleted_count += 1
        gr.Info(f"Successfully deleted {deleted_count} selected content item(s).")
    except Exception as e:
        gr.Warning(f"Error during deletion: {str(e)}")
    return update_library_view()



def load_suggested_questions(course_id: str):
    """Load suggested example questions for the selected course."""
    if not course_id:
        return [gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)]
    try:
        course = library.get_course(course_id)
        if course.embedding_status != "completed":
            return [gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)]
        
        questions = ai_tools.generate_suggested_questions(course_id)
        updates = []
        for i in range(3):
            if i < len(questions):
                updates.append(gr.update(value=questions[i], visible=True))
            else:
                updates.append(gr.update(visible=False))
        return updates
    except Exception as e:
        print(f"Error loading suggested questions: {e}")
        return [gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)]



def chat_manual(user_message: str, history: list, course_id: str):
    """Handle a chat message from the user."""
    if not course_id:
        gr.Warning("Select a course from the sidebar before chatting.")
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": "Please select a course from the dropdown first."})
        return "", history, "<p>Please select a course.</p>"

    res = generator.generate(course_id, user_message)
    data = res["structured"]
    sources = res["sources"]

    if data.get("key_concepts"):
        analytics_tracker.log_question_asked(course_id, data["key_concepts"])
    else:
        analytics_tracker.log_question_asked(course_id, ["General"])

    # ── Build beautifully formatted HTML response ──
    answer_text = data.get('main_answer', '')
    confidence = data.get('confidence_score', 0)

    # Confidence color
    if confidence >= 80:
        conf_color, conf_label = '#10B981', 'High'
    elif confidence >= 50:
        conf_color, conf_label = '#F59E0B', 'Medium'
    else:
        conf_color, conf_label = '#EF4444', 'Low'

    md = f"""<div style="font-family: 'Inter', system-ui, sans-serif; line-height: 1.7; color: #1F2937;">

<div style="margin-bottom: 16px; font-size: 14px; color: #374151;">
{answer_text}
</div>

<div style="display: inline-flex; align-items: center; gap: 6px; background: {conf_color}12; border: 1px solid {conf_color}30; border-radius: 20px; padding: 3px 12px; margin-bottom: 14px;">
  <span style="width: 7px; height: 7px; border-radius: 50%; background: {conf_color}; display: inline-block;"></span>
  <span style="font-size: 11px; font-weight: 600; color: {conf_color};">{conf_label} Confidence ({confidence}%)</span>
</div>
"""

    # Key Concepts as styled chips
    if data.get("key_concepts"):
        chips = ''.join([
            f'<span style="display: inline-block; background: #EEF2FF; color: #4338CA; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; margin: 2px 4px 2px 0;">{c}</span>'
            for c in data['key_concepts']
        ])
        md += f"""
<div style="margin-bottom: 14px;">
  <div style="font-size: 12px; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">📚 Key Concepts</div>
  <div>{chips}</div>
</div>
"""

    # Practice Questions as a styled list
    if data.get("practice_questions"):
        questions_html = ''
        difficulty_colors = {'Easy': '#10B981', 'Medium': '#F59E0B', 'Hard': '#EF4444'}
        for q in data["practice_questions"]:
            diff = q.get('difficulty', 'Easy')
            color = difficulty_colors.get(diff, '#6B7280')
            questions_html += f"""
<div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
  <span style="display: inline-block; background: {color}18; color: {color}; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px; flex-shrink: 0; margin-top: 2px;">{diff}</span>
  <span style="font-size: 13px; color: #374151;">{q.get('question', '')}</span>
</div>"""
        md += f"""
<div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 10px; padding: 14px; margin-bottom: 14px;">
  <div style="font-size: 12px; font-weight: 700; color: #7C3AED; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">🧠 Practice Questions</div>
  {questions_html}
</div>
"""

    # Related Topics
    if data.get("related_topics"):
        topics = ' → '.join([f'<span style="font-weight: 600; color: #4F46E5;">{t}</span>' for t in data['related_topics']])
        md += f"""
<div style="margin-bottom: 14px;">
  <div style="font-size: 12px; font-weight: 700; color: #0891B2; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">🔗 Study Next</div>
  <div style="font-size: 13px; color: #374151;">{topics}</div>
</div>
"""

    # Learning Tips
    if data.get("learning_tips"):
        md += f"""
<div style="background: #FFFBEB; border-left: 3px solid #F59E0B; border-radius: 0 8px 8px 0; padding: 10px 14px; margin-bottom: 10px;">
  <div style="font-size: 12px; font-weight: 700; color: #D97706; margin-bottom: 3px;">💡 Learning Tip</div>
  <div style="font-size: 13px; color: #92400E;">{data['learning_tips']}</div>
</div>
"""

    md += "</div>"

    timeline_html = build_timeline_html(sources)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": md})
    return "", history, timeline_html


def run_quiz(course_id: str):
    """Generate a quiz for the selected course."""
    if not course_id:
        gr.Warning("Select a course first.")
        return gr.update(value="Select a course first.", visible=True)
    gr.Info("Generating quiz...")
    result = ai_tools.generate_quiz(course_id)
    return gr.update(value=result, visible=True)


def run_notes(course_id: str, topic: str):
    """Generate revision notes for the selected course based on a topic."""
    if not course_id:
        gr.Warning("Select a course first.")
        return gr.update(value="Select a course first.", visible=True)
    if not topic or not topic.strip():
        gr.Warning("Please enter a topic name.")
        return gr.update(value="Please enter a topic name.", visible=True)
    gr.Info(f"Generating revision notes for '{topic}'...")
    result = ai_tools.generate_revision_notes(course_id, topic.strip())
    return gr.update(value=result, visible=True)


# ═══════════════════════════════════════════════════════════════════════
# UI LAYER — DESIGN SYSTEM CSS (v3 — Production-Grade Light Theme)
# ═══════════════════════════════════════════════════════════════════════

CUSTOM_CSS = r"""
/* ── Font Import ──────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ═══════════════════════════════════════════════════════════════
   Override Gradio 6.x theme variables at root level
   This forces the entire app into our light theme
   ═══════════════════════════════════════════════════════════════ */
:root, .gradio-container, body, .dark {
  --body-background-fill: #FFFFFF !important;
  --background-fill-primary: #FFFFFF !important;
  --background-fill-secondary: #F7F8FA !important;
  --block-background-fill: #FFFFFF !important;
  --block-border-color: #E5E7EB !important;
  --block-label-background-fill: #FFFFFF !important;
  --block-label-border-color: #E5E7EB !important;
  --block-label-text-color: #374151 !important;
  --block-title-text-color: #111827 !important;
  --body-text-color: #111827 !important;
  --body-text-color-subdued: #6B7280 !important;
  --border-color-accent: #4F46E5 !important;
  --border-color-primary: #E5E7EB !important;
  --button-primary-background-fill: #4F46E5 !important;
  --button-primary-background-fill-hover: #4338CA !important;
  --button-primary-text-color: #FFFFFF !important;
  --button-secondary-background-fill: #FFFFFF !important;
  --button-secondary-background-fill-hover: #F3F4F6 !important;
  --button-secondary-border-color: #D1D5DB !important;
  --button-secondary-text-color: #374151 !important;
  --checkbox-background-color: #FFFFFF !important;
  --checkbox-background-color-selected: #4F46E5 !important;
  --checkbox-border-color: #D1D5DB !important;
  --checkbox-border-color-selected: #4F46E5 !important;
  --checkbox-check-color: #FFFFFF !important;
  --checkbox-label-background-fill: #F3F4F6 !important;
  --checkbox-label-background-fill-selected: rgba(79,70,229,0.08) !important;
  --checkbox-label-background-fill-hover: #E5E7EB !important;
  --checkbox-label-text-color: #374151 !important;
  --checkbox-label-text-color-selected: #4F46E5 !important;
  --color-accent: #4F46E5 !important;
  --color-accent-soft: rgba(79,70,229,0.08) !important;
  --input-background-fill: #FFFFFF !important;
  --input-border-color: #D1D5DB !important;
  --input-border-color-focus: #4F46E5 !important;
  --link-text-color: #4F46E5 !important;
  --link-text-color-hover: #4338CA !important;
  --neutral-50: #F9FAFB !important;
  --neutral-100: #F3F4F6 !important;
  --neutral-200: #E5E7EB !important;
  --neutral-300: #D1D5DB !important;
  --neutral-400: #9CA3AF !important;
  --neutral-500: #6B7280 !important;
  --neutral-600: #4B5563 !important;
  --neutral-700: #374151 !important;
  --neutral-800: #1F2937 !important;
  --neutral-900: #111827 !important;
  --neutral-950: #030712 !important;
  --shadow-drop: 0 1px 3px 0 rgba(0,0,0,0.06), 0 1px 2px -1px rgba(0,0,0,0.06) !important;
  --shadow-drop-lg: 0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -4px rgba(0,0,0,0.06) !important;
  --table-border-color: #E5E7EB !important;
  --table-row-focus: rgba(79,70,229,0.04) !important;

  /* Our custom design tokens */
  --ll-brand: #4F46E5;
  --ll-brand-hover: #4338CA;
  --ll-brand-light: #6366F1;
  --ll-brand-bg: rgba(79,70,229,0.05);
  --ll-brand-bg-2: rgba(79,70,229,0.08);
  --ll-text-1: #111827;
  --ll-text-2: #4B5563;
  --ll-text-3: #9CA3AF;
  --ll-border: #E5E7EB;
  --ll-border-hover: #D1D5DB;
  --ll-surface: #FFFFFF;
  --ll-surface-2: #F7F8FA;
  --ll-surface-3: #F3F4F6;
  --ll-success: #059669;
  --ll-warning: #D97706;
  --ll-error: #DC2626;
  --ll-radius-sm: 6px;
  --ll-radius-md: 8px;
  --ll-radius-lg: 12px;
  --ll-radius-xl: 16px;
  --ll-shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --ll-shadow-md: 0 4px 6px -1px rgba(0,0,0,0.06), 0 2px 4px -2px rgba(0,0,0,0.06);
  --ll-shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -4px rgba(0,0,0,0.06);
  --ll-font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Force light mode even if system/Hugging Face prefers dark */
.dark {
  background: #FFFFFF !important;
  color: #111827 !important;
}

/* Checkbox and File fixes */
#ll-library-checkboxes label, .gradio-checkbox-group label {
  background: #F3F4F6 !important;
  color: #374151 !important;
  border-color: #D1D5DB !important;
}
#ll-library-checkboxes label:hover, .gradio-checkbox-group label:hover {
  background: #E5E7EB !important;
}
#ll-library-checkboxes label.selected, .gradio-checkbox-group label.selected {
  background: rgba(79,70,229,0.08) !important;
  color: #4F46E5 !important;
  border-color: #4F46E5 !important;
}
#ll-library-checkboxes input:checked, .gradio-checkbox-group input:checked {
  background-color: #4F46E5 !important;
  border-color: #4F46E5 !important;
  background-image: url("data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e") !important;
  background-size: 100% 100% !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
}
.file-preview-holder, .file-preview, .file, .file-name, tbody tr, .file-preview-item {
  background: #F9FAFB !important;
  color: #111827 !important;
}
.file-size, .icon {
  color: #4B5563 !important;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* ═══════════════════════════════════════════════════════════════
   Global Reset — force white backgrounds everywhere
   ═══════════════════════════════════════════════════════════════ */
body {
  font-family: var(--ll-font) !important;
  background: #FFFFFF !important;
  color: var(--ll-text-1) !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
}
.gradio-container {
  font-family: var(--ll-font) !important;
  background: #FFFFFF !important;
  max-width: none !important;
  width: 100% !important;
  margin: 0 !important;
  padding: 16px 24px !important;
}
.gradio-container > .main, .gradio-container > .wrap, .gradio-container .contain {
  max-width: none !important;
  width: 100% !important;
}
footer { display: none !important; }
.app { background: #FFFFFF !important; max-width: none !important; }

/* ═══════════════════════════════════════════════════════════════
   Hero Header — compact, professional
   ═══════════════════════════════════════════════════════════════ */
.ll-hero {
  background: #FFFFFF;
  border: 1px solid var(--ll-border);
  border-radius: var(--ll-radius-xl);
  padding: 24px 32px 20px;
  margin-bottom: 16px;
  box-shadow: var(--ll-shadow-sm);
}
.ll-hero-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 4px;
}
.ll-hero-logo {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.25);
}
.ll-hero-logo svg { width: 18px; height: 18px; color: #fff; stroke-width: 1.5; }
.ll-hero h1 {
  font-size: 32px !important; font-weight: 800 !important;
  letter-spacing: -1px !important;
  color: #111827 !important;
  margin: 0 !important; padding: 0 !important;
  line-height: 32px !important;
  position: relative;
  top: -2px;
}
.ll-hero h1 span { 
  background: linear-gradient(135deg, #4f46e5 0%, #ec4899 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.ll-hero-tagline {
  font-size: 13px !important; color: var(--ll-text-2) !important;
  margin: 8px auto 0 !important; line-height: 1.5 !important;
  max-width: 600px !important;
  text-align: center !important;
}

/* ── Pipeline Steps ───────────────────────────────────────────── */
.ll-pipeline {
  display: flex;
  align-items: center;
  gap: 0;
  margin-top: 16px;
}
.ll-pipe-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--ll-surface-2);
  border: 1px solid var(--ll-border);
  border-radius: var(--ll-radius-md);
  flex: 1;
  min-width: 0;
  transition: all 150ms ease;
}
.ll-pipe-step:hover {
  border-color: var(--ll-brand);
  background: var(--ll-brand-bg);
}
.ll-pipe-icon {
  width: 30px; height: 30px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.ll-pipe-icon svg { width: 15px; height: 15px; }
.ll-pipe-icon-1 { background: rgba(79,70,229,0.07); color: var(--ll-brand); }
.ll-pipe-icon-2 { background: rgba(124,58,237,0.07); color: #7C3AED; }
.ll-pipe-icon-3 { background: rgba(8,145,178,0.07); color: #0891B2; }
.ll-pipe-text { min-width: 0; }
.ll-pipe-label {
  display: block;
  font-size: 9px; font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--ll-text-3);
  margin-bottom: 0;
}
.ll-pipe-title {
  display: block;
  font-size: 12px; font-weight: 600;
  color: var(--ll-text-1);
}
.ll-pipe-arrow {
  display: flex; align-items: center; justify-content: center;
  padding: 0 4px;
  color: var(--ll-text-3);
  flex-shrink: 0;
}
.ll-pipe-arrow svg { width: 14px; height: 14px; }

/* ═══════════════════════════════════════════════════════════════
   Sidebar
   ═══════════════════════════════════════════════════════════════ */
.ll-sidebar-col {
  background: #FFFFFF !important;
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-xl) !important;
  padding: 16px !important;
  box-shadow: var(--ll-shadow-sm) !important;
}
.ll-delete-btn {
  background: #FFFFFF !important;
  border: 1px solid #FCA5A5 !important;
  color: #DC2626 !important;
  transition: all 150ms ease !important;
  margin-top: 4px !important;
  width: 100% !important;
}
.ll-delete-btn:hover {
  background: #FEF2F2 !important;
  border-color: #EF4444 !important;
  color: #B91C1C !important;
}

/* Sleek Suggested Question Chips */
#ll-example-questions-row {
  gap: 8px !important;
  margin-top: 6px !important;
  margin-bottom: 12px !important;
}
.ll-example-q-btn {
  background: var(--ll-surface-2) !important;
  border: 1px solid var(--ll-border) !important;
  color: var(--ll-text-2) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  padding: 6px 12px !important;
  border-radius: 9999px !important;
  transition: all 120ms ease !important;
  cursor: pointer !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  display: inline-block !important;
  max-width: 100% !important;
  box-shadow: none !important;
}
.ll-example-q-btn:hover {
  background: var(--ll-brand-bg-2) !important;
  border-color: var(--ll-brand) !important;
  color: var(--ll-brand) !important;
}


/* ═══════════════════════════════════════════════════════════════
   Tabs — clean pill style
   ═══════════════════════════════════════════════════════════════ */
.tabs { border: none !important; }
.tab-nav {
  background: var(--ll-surface-3) !important;
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  padding: 3px !important;
  gap: 2px !important;
  margin-bottom: 16px !important;
  box-shadow: none !important;
}
.tab-nav button {
  border: none !important;
  border-radius: var(--ll-radius-md) !important;
  font-family: var(--ll-font) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 8px 18px !important;
  color: var(--ll-text-2) !important;
  background: transparent !important;
  transition: all 150ms ease !important;
}
.tab-nav button:hover {
  background: #FFFFFF !important;
  color: var(--ll-text-1) !important;
}
.tab-nav button.selected {
  background: #FFFFFF !important;
  color: var(--ll-text-1) !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}

/* ═══════════════════════════════════════════════════════════════
   Buttons
   ═══════════════════════════════════════════════════════════════ */
.primary, button.primary {
  background: var(--ll-brand) !important;
  border: none !important;
  border-radius: var(--ll-radius-md) !important;
  font-family: var(--ll-font) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 10px 24px !important;
  color: #fff !important;
  transition: all 150ms ease !important;
  box-shadow: 0 1px 2px rgba(79,70,229,0.15) !important;
}
.primary:hover, button.primary:hover {
  background: var(--ll-brand-hover) !important;
  box-shadow: 0 2px 6px rgba(79,70,229,0.2) !important;
}
button, .btn {
  font-family: var(--ll-font) !important;
  border-radius: var(--ll-radius-md) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
}
button:focus-visible {
  outline: 2px solid var(--ll-brand) !important;
  outline-offset: 2px !important;
}

/* ═══════════════════════════════════════════════════════════════
   Inputs
   ═══════════════════════════════════════════════════════════════ */
input, textarea, select, .wrap {
  font-family: var(--ll-font) !important;
  border-radius: var(--ll-radius-md) !important;
  background: #FFFFFF !important;
  border-color: var(--ll-border) !important;
  color: var(--ll-text-1) !important;
  font-size: 13px !important;
}
input:focus, textarea:focus, select:focus {
  border-color: var(--ll-brand) !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.08) !important;
}
label, .label-wrap {
  color: var(--ll-text-2) !important;
  font-family: var(--ll-font) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

/* ═══════════════════════════════════════════════════════════════
   Chatbot — production chat UI
   ═══════════════════════════════════════════════════════════════ */
#ll-chatbot {
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  background: #FFFFFF !important;
  box-shadow: none !important;
}
#ll-chatbot .placeholder {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 100% !important;
  font-family: var(--ll-font) !important;
  font-size: 16px !important;
  font-weight: 500 !important;
  color: var(--ll-text-3) !important;
  letter-spacing: -0.2px !important;
  text-align: center !important;
  padding: 40px !important;
  opacity: 0.7 !important;
}
.message {
  font-family: var(--ll-font) !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
}
.message.bot .content, .message.bot .message-content {
  background: var(--ll-surface-2) !important;
  border: 1px solid var(--ll-border) !important;
  border-radius: 12px 12px 12px 4px !important;
  color: var(--ll-text-1) !important;
}
.message.user p, .message.user span, .message.user div {
  color: #111827 !important;
  font-weight: 600 !important;
}
.message.user .content, .message.user .message-content {
  background: #F3F4F6 !important;
  border: 1px solid #E5E7EB !important;
  border-radius: 12px 12px 4px 12px !important;
}

/* ═══════════════════════════════════════════════════════════════
   Library Items
   ═══════════════════════════════════════════════════════════════ */
.ll-lib-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: var(--ll-radius-md);
  transition: all 150ms ease;
  margin-bottom: 2px;
  cursor: pointer;
}
.ll-lib-item:hover {
  border-color: var(--ll-border);
  background: var(--ll-surface-2);
}
.ll-lib-icon {
  width: 28px; height: 28px;
  background: var(--ll-brand-bg-2);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  color: var(--ll-brand);
}
.ll-lib-icon svg { width: 14px; height: 14px; }
.ll-lib-info { flex: 1; min-width: 0; }
.ll-lib-name {
  display: block; font-size: 13px; font-weight: 500;
  color: var(--ll-text-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ll-lib-status {
  display: block; font-size: 11px; margin-top: 1px; font-weight: 500;
}
.ll-status-ok { color: var(--ll-success); }
.ll-status-pending { color: var(--ll-warning); }
.ll-status-error { color: var(--ll-error); }
.ll-empty-lib {
  font-size: 13px; color: var(--ll-text-3); padding: 8px 0;
}

/* ═══════════════════════════════════════════════════════════════
   Status & Branding
   ═══════════════════════════════════════════════════════════════ */
.ll-model-status {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 0; font-size: 12px; color: var(--ll-text-2);
}
.ll-pulse-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--ll-success);
  flex-shrink: 0;
}
.ll-branding {
  text-align: center; margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--ll-border);
  color: var(--ll-text-3); font-size: 11px;
  line-height: 1.7;
}
.ll-branding strong { color: var(--ll-text-2); font-weight: 600; }
.ll-branding a {
  color: var(--ll-brand); text-decoration: none; font-weight: 500;
}
.ll-branding a:hover { color: var(--ll-brand-hover); text-decoration: underline; }

/* ═══════════════════════════════════════════════════════════════
   Tool Buttons
   ═══════════════════════════════════════════════════════════════ */
.ll-tool-btn {
  background: #FFFFFF !important;
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  padding: 14px 20px !important;
  font-weight: 500 !important;
  color: var(--ll-text-1) !important;
  transition: all 150ms ease !important;
  font-size: 13px !important;
}
.ll-tool-btn:hover {
  border-color: var(--ll-brand) !important;
  color: var(--ll-brand) !important;
  background: var(--ll-brand-bg) !important;
  box-shadow: var(--ll-shadow-md) !important;
}

/* ═══════════════════════════════════════════════════════════════
   File Upload
   ═══════════════════════════════════════════════════════════════ */
.upload-area, .file-upload {
  border: 1.5px dashed var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  background: var(--ll-surface-2) !important;
  transition: all 150ms !important;
}
.upload-area:hover, .file-upload:hover {
  border-color: var(--ll-brand) !important;
  background: var(--ll-brand-bg) !important;
}

/* ═══════════════════════════════════════════════════════════════
   Cards / Panels
   ═══════════════════════════════════════════════════════════════ */
.panel, .form {
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  background: #FFFFFF !important;
}

/* ═══════════════════════════════════════════════════════════════
   Markdown & Document Output
   ═══════════════════════════════════════════════════════════════ */
.ll-document-output {
  max-width: 850px !important;
  margin: 0 auto !important;
  padding: 32px !important;
  background: #FFFFFF !important;
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  box-shadow: var(--ll-shadow-sm) !important;
}
.prose h1, .prose h2, .prose h3,
.markdown-text h1, .markdown-text h2, .markdown-text h3 {
  font-family: var(--ll-font) !important;
  color: var(--ll-text-1) !important;
  letter-spacing: -0.3px !important;
  margin-top: 1.5em !important;
  margin-bottom: 0.5em !important;
}
.prose, .markdown-text {
  font-family: var(--ll-font) !important;
  color: var(--ll-text-1) !important;
  line-height: 1.7 !important;
  font-size: 15px !important;
}
.prose code, .markdown-text code {
  background: var(--ll-brand-bg-2) !important;
  border-radius: 4px !important;
  padding: 2px 6px !important;
  font-size: 13.5px !important;
  color: var(--ll-brand) !important;
  font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}
.prose pre, .markdown-text pre {
  background: #111827 !important;
  color: #E5E7EB !important;
  padding: 16px !important;
  border-radius: var(--ll-radius-md) !important;
  overflow-x: auto !important;
  margin: 16px 0 !important;
  border: 1px solid #374151 !important;
}
.prose pre code, .markdown-text pre code {
  background: transparent !important;
  color: inherit !important;
  padding: 0 !important;
}
.prose pre span, .markdown-text pre span {
  color: inherit !important;
}
.prose ul, .markdown-text ul, .prose ol, .markdown-text ol {
  padding-left: 24px !important;
  margin-bottom: 16px !important;
}
.prose li, .markdown-text li {
  margin-bottom: 8px !important;
}
.prose blockquote, .markdown-text blockquote {
  border-left: 4px solid var(--ll-brand) !important;
  color: var(--ll-text-2) !important;
  font-style: italic !important;
  margin: 16px 0 !important;
  background: var(--ll-surface-2) !important;
  padding: 12px 16px !important;
  border-radius: 0 var(--ll-radius-md) var(--ll-radius-md) 0 !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }

/* ── Loading Spinner Containment ─────────────────────────────── */
.wrap, .pending, .generating {
  position: relative !important;
  overflow: hidden !important;
}
.progress-bar, .progress-text, .eta-bar,
.meta-text, .meta-text-center {
  position: absolute !important;
  z-index: 10 !important;
}
.gradio-container .column > *, .gradio-container .row > * {
  position: relative !important;
  overflow: hidden !important;
}

/* ═══════════════════════════════════════════════════════════════
   Section Headers
   ═══════════════════════════════════════════════════════════════ */
.ll-section-header {
  display: flex; align-items: flex-start; gap: 10px;
  margin-bottom: 14px;
}
.ll-section-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}
.ll-section-title {
  font-size: 15px; font-weight: 600;
  color: var(--ll-text-1);
  letter-spacing: -0.2px;
  line-height: 1.3;
}
.ll-section-sub {
  font-size: 13px; color: var(--ll-text-3);
  line-height: 1.45; margin-top: 2px;
}

/* ═══════════════════════════════════════════════════════════════
   Format Badges
   ═══════════════════════════════════════════════════════════════ */
.ll-formats {
  display: flex; flex-wrap: wrap; gap: 5px;
  margin-top: 10px;
}
.ll-format-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px;
  background: var(--ll-surface-2);
  border: 1px solid var(--ll-border);
  border-radius: 9999px;
  font-size: 11px; font-weight: 500;
  color: var(--ll-text-2);
  transition: all 150ms;
}
.ll-format-badge:hover {
  border-color: var(--ll-brand);
  color: var(--ll-brand);
}
.ll-format-badge svg { width: 12px; height: 12px; flex-shrink: 0; }

/* ═══════════════════════════════════════════════════════════════
   Transcript Viewer
   ═══════════════════════════════════════════════════════════════ */
.tv-container {
  border: 1px solid var(--ll-border);
  border-radius: var(--ll-radius-lg);
  background: #FFFFFF;
  overflow: hidden;
}
.tv-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--ll-border);
  background: var(--ll-surface-2);
}
.tv-header-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600;
  color: var(--ll-text-1);
}
.tv-header-title svg { color: var(--ll-brand); width: 15px; height: 15px; }
.tv-stats { display: flex; gap: 5px; flex-wrap: wrap; }
.tv-stat-chip {
  padding: 2px 8px;
  background: var(--ll-brand-bg-2);
  border-radius: 9999px;
  font-size: 11px; font-weight: 500;
  color: var(--ll-brand);
}
.tv-segments {
  max-height: 400px;
  overflow-y: auto;
  padding: 6px;
}
.tv-segment {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  transition: all 120ms;
  cursor: pointer;
  margin-bottom: 1px;
}
.tv-segment:hover { background: var(--ll-brand-bg); }
.tv-timestamp {
  flex-shrink: 0;
  font-size: 11px; font-weight: 600;
  color: var(--ll-brand);
  background: var(--ll-brand-bg-2);
  padding: 2px 6px;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
  margin-top: 1px;
}
.tv-text {
  font-size: 13px; line-height: 1.5;
  color: var(--ll-text-2);
}
.tv-empty {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 40px 20px; text-align: center;
}
.tv-empty-icon { color: var(--ll-text-3); margin-bottom: 10px; opacity: 0.35; }
.tv-empty-title {
  font-size: 14px; font-weight: 600;
  color: var(--ll-text-2); margin: 0 0 4px;
}
.tv-empty-sub {
  font-size: 13px; color: var(--ll-text-3);
  margin: 0; max-width: 240px; line-height: 1.45;
}
.tv-processing-spinner {
  width: 28px; height: 28px;
  border: 2px solid var(--ll-border);
  border-top-color: var(--ll-brand);
  border-radius: 50%;
  animation: ll-spin 0.8s linear infinite;
  margin-bottom: 10px;
}
@keyframes ll-spin { to { transform: rotate(360deg); } }

/* ═══════════════════════════════════════════════════════════════
   Dashboard Styles
   ═══════════════════════════════════════════════════════════════ */
.dash-container { padding: 0; }
.dash-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.dash-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px;
  background: #FFFFFF;
  border: 1px solid var(--ll-border);
  border-radius: var(--ll-radius-lg);
  transition: all 150ms;
}
.dash-card:hover {
  box-shadow: var(--ll-shadow-md);
}
.dash-card-icon {
  width: 36px; height: 36px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.dash-card-info { min-width: 0; }
.dash-card-value {
  display: block;
  font-size: 20px; font-weight: 700;
  color: var(--ll-text-1);
  letter-spacing: -0.3px;
}
.dash-card-label {
  display: block;
  font-size: 11px; font-weight: 500;
  color: var(--ll-text-3);
  margin-top: 1px;
}
.dash-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}
.dash-section {
  background: #FFFFFF;
  border: 1px solid var(--ll-border);
  border-radius: var(--ll-radius-lg);
  padding: 14px;
}
.dash-section-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 600;
  color: var(--ll-text-1);
  margin: 0 0 12px;
}
.dash-section-title svg { color: var(--ll-brand); width: 15px; height: 15px; }
.dash-bars { display: flex; flex-direction: column; gap: 8px; }
.dash-bar-row { display: flex; align-items: center; gap: 8px; }
.dash-bar-label {
  flex-shrink: 0; width: 72px;
  font-size: 12px; font-weight: 500;
  color: var(--ll-text-2);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dash-bar-track {
  flex: 1; height: 5px;
  background: var(--ll-surface-3);
  border-radius: 3px;
  overflow: hidden;
}
.dash-bar-fill {
  height: 100%;
  background: var(--ll-brand);
  border-radius: 3px;
  transition: width 400ms ease;
}
.dash-bar-count {
  flex-shrink: 0; width: 24px;
  font-size: 12px; font-weight: 600;
  color: var(--ll-text-2);
  text-align: right;
}
.dash-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.dash-tag {
  padding: 3px 8px;
  border-radius: 9999px;
  font-size: 11px; font-weight: 500;
}
.dash-tag-weak {
  background: rgba(217,119,6,0.06);
  color: var(--ll-warning);
  border: 1px solid rgba(217,119,6,0.12);
}
.dash-tag-strong {
  background: rgba(5,150,105,0.06);
  color: var(--ll-success);
  border: 1px solid rgba(5,150,105,0.12);
}
.dash-area-label {
  font-size: 12px; font-weight: 500;
  color: var(--ll-text-3); margin: 0 0 4px;
}
.dash-activity {
  display: flex; flex-direction: column; gap: 4px;
  max-height: 180px; overflow-y: auto;
}
.dash-activity-item {
  padding: 6px 10px;
  background: var(--ll-surface-2);
  border: 1px solid var(--ll-border);
  border-radius: 6px;
  font-size: 12px;
  color: var(--ll-text-2);
}
.dash-empty-state {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 40px 20px; text-align: center;
}
.dash-empty-hint {
  font-size: 13px; color: var(--ll-text-3); margin: 0;
}

/* ═══════════════════════════════════════════════════════════════
   Timeline
   ═══════════════════════════════════════════════════════════════ */
.timeline-container {
  border: 1px solid var(--ll-border) !important;
  border-radius: var(--ll-radius-lg) !important;
  background: #FFFFFF !important;
  padding: 12px !important;
}
.timeline-container h3 {
  color: var(--ll-text-1) !important;
  font-family: var(--ll-font) !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  margin-top: 0 !important;
}
.timeline-container button {
  background: var(--ll-brand) !important;
  border: none !important;
  border-radius: 6px !important;
  padding: 5px 12px !important;
  cursor: pointer !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  color: #fff !important;
}
.timeline-container button:hover {
  background: var(--ll-brand-hover) !important;
}
.timeline-container span {
  color: var(--ll-text-2) !important;
  font-family: var(--ll-font) !important;
  font-size: 13px !important;
}

/* ═══════════════════════════════════════════════════════════════
   Responsive
   ═══════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .gradio-container { padding: 8px !important; }
  .ll-hero { padding: 16px !important; }
  .ll-pipeline { flex-direction: column; }
  .ll-pipe-arrow { transform: rotate(90deg); }
  .tab-nav button { padding: 6px 10px !important; font-size: 12px !important; }
  .dash-grid-2 { grid-template-columns: 1fr; }
}
"""


# ═══════════════════════════════════════════════════════════════════════
# UI LAYER — SVG ICONS (professional, no emojis)
# ═══════════════════════════════════════════════════════════════════════

ICON_LAYERS = '<svg viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:22px;height:22px;"><path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.84Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>'

ARROW_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>'

# Small inline SVG icons for format badges
BADGE_VIDEO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
BADGE_DOC = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6"/></svg>'
BADGE_LINK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'


# ═══════════════════════════════════════════════════════════════════════
# CREATE APP
# ═══════════════════════════════════════════════════════════════════════

def create_app() -> gr.Blocks:
    """Build and return the Gradio application."""
    app_theme = gr.themes.Default(
        font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        primary_hue="indigo",
        neutral_hue="gray",
        radius_size=gr.themes.sizes.radius_md,
    )

    with gr.Blocks(
        title="LearnLens AI",
        theme=app_theme,
        fill_width=True,
        css=CUSTOM_CSS,
    ) as app:

        # ── Hero Header ──────────────────────────────────────────
        gr.HTML(f"""
        <div class="ll-hero">
            <div class="ll-hero-top">
                <h1>LearnLens <span>AI</span></h1>
            </div>
            <p class="ll-hero-tagline">Transform video and document content into searchable knowledge. Upload content, extract text with AI, and query it using RAG-powered Q&amp;A.</p>

            <div class="ll-pipeline">
                <div class="ll-pipe-step">
                    <div class="ll-pipe-icon ll-pipe-icon-1">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    </div>
                    <div class="ll-pipe-text">
                        <span class="ll-pipe-label">Step 1</span>
                        <span class="ll-pipe-title">Upload Content</span>
                    </div>
                </div>
                <div class="ll-pipe-arrow">{ARROW_SVG}</div>
                <div class="ll-pipe-step">
                    <div class="ll-pipe-icon ll-pipe-icon-2">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>
                    </div>
                    <div class="ll-pipe-text">
                        <span class="ll-pipe-label">Step 2</span>
                        <span class="ll-pipe-title">Extract Text</span>
                    </div>
                </div>
                <div class="ll-pipe-arrow">{ARROW_SVG}</div>
                <div class="ll-pipe-step">
                    <div class="ll-pipe-icon ll-pipe-icon-3">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    </div>
                    <div class="ll-pipe-text">
                        <span class="ll-pipe-label">Step 3</span>
                        <span class="ll-pipe-title">Query and Chat</span>
                    </div>
                </div>
            </div>
        </div>
        """)

        with gr.Row():
            # ── SIDEBAR ──────────────────────────────────────────
            with gr.Column(scale=1, min_width=240, elem_classes="ll-sidebar-col"):
                course_dropdown = gr.Dropdown(
                    label="Active Course",
                    interactive=True,
                    elem_id="ll-course-dropdown",
                )
                refresh_btn = gr.Button("Refresh Library", size="sm")
                library_checkboxes = gr.CheckboxGroup(
                    choices=[],
                    label="Select Content to Delete",
                    elem_id="ll-library-checkboxes",
                )
                delete_btn = gr.Button("Delete Selected", variant="secondary", size="sm", elem_classes="ll-delete-btn")
                gr.Markdown("---")
                library_display = gr.HTML(
                    "<p class='ll-empty-lib'>No content uploaded yet.</p>",
                    elem_id="ll-library-display",
                )

                gr.HTML(f"""
                <div class="ll-model-status">
                    <div class="ll-pulse-dot"></div>
                    <span>{MODEL_DISPLAY_NAME} &middot; Ready</span>
                </div>
                """)

                gr.HTML("""
                <div class="ll-branding">
                    LearnLens AI <br>
                    Built by <strong>Om Makwana</strong><br>
                    <a href="https://github.com/MakwanaOm1615" target="_blank" rel="noopener">GitHub</a>
                    &middot;
                    <a href="https://www.linkedin.com/in/om-makwana-490aa7239/" target="_blank" rel="noopener">LinkedIn</a>
                </div>
                """)

            # ── MAIN CONTENT ─────────────────────────────────────
            with gr.Column(scale=4):
                with gr.Tabs():
                    # ── Tab 1: Upload ─────────────────────────────
                    with gr.Tab("Upload"):
                        gr.HTML(f"""
                        <div class="ll-section-header">
                            <div class="ll-section-icon" style="background:rgba(79,70,229,0.06); color:#4F46E5;">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            </div>
                            <div>
                                <div class="ll-section-title">Upload Content</div>
                                <div class="ll-section-sub">Add a video, document, or YouTube URL. AI will transcribe and index the content for Q&amp;A.</div>
                            </div>
                        </div>
                        <div class="ll-formats">
                            <span class="ll-format-badge">{BADGE_VIDEO} MP4</span>
                            <span class="ll-format-badge">{BADGE_DOC} PDF</span>
                            <span class="ll-format-badge">{BADGE_DOC} DOCX</span>
                            <span class="ll-format-badge">{BADGE_DOC} TXT</span>
                            <span class="ll-format-badge">{BADGE_LINK} YouTube URL</span>
                        </div>
                        """)
                        with gr.Row():
                            v_upload = gr.File(
                                label="Upload File (MP4, PDF, DOCX, TXT)",
                                file_types=["video", ".pdf", ".docx", ".txt"],
                            )
                            with gr.Column():
                                v_url = gr.Textbox(
                                    label="Or paste a public video URL",
                                    placeholder="https://youtube.com/watch?v=...",
                                )
                                v_title = gr.Textbox(
                                    label="Title (optional)",
                                    placeholder="e.g. Machine Learning Lecture 1",
                                )
                        upload_btn = gr.Button("Upload and Process", variant="primary")
                        upload_status = gr.Markdown("")

                    # ── Tab 2: Ask AI ─────────────────────────────
                    with gr.Tab("Ask AI"):
                        with gr.Row():
                            with gr.Column(scale=2):
                                chatbot = gr.Chatbot(
                                    height=450,
                                    label="AI Tutor",
                                    sanitize_html=False,
                                    placeholder="Select a course and type a question below to start.",
                                    elem_id="ll-chatbot",
                                )
                                with gr.Row(elem_id="ll-example-questions-row"):
                                    q_btn1 = gr.Button("", visible=False, size="sm", elem_classes="ll-example-q-btn")
                                    q_btn2 = gr.Button("", visible=False, size="sm", elem_classes="ll-example-q-btn")
                                    q_btn3 = gr.Button("", visible=False, size="sm", elem_classes="ll-example-q-btn")
                                with gr.Row():
                                    msg = gr.Textbox(
                                        placeholder="Ask anything about your content...",
                                        container=False,
                                        show_label=False,
                                        scale=5,
                                        elem_id="ll-chat-input",
                                    )
                                    send_btn = gr.Button("Send", variant="primary", scale=1, min_width=72)
                                clear = gr.ClearButton([msg, chatbot], value="Clear")
                            with gr.Column(scale=1, visible=False) as right_column:
                                course_video = gr.Video(label="Content Player")
                                timeline_display = gr.HTML(
                                    "<p style='color:#9CA3AF;font-size:13px;text-align:center;padding:12px;'>Ask a question to see relevant timestamps.</p>"
                                )


                    # ── Tab 4: Study Tools ────────────────────────
                    with gr.Tab("Study Tools"):
                        gr.HTML(f"""
                        <div class="ll-section-header">
                            <div class="ll-section-icon" style="background:rgba(8,145,178,0.06); color:#0891B2;">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
                            </div>
                            <div>
                                <div class="ll-section-title">AI Study Tools</div>
                                <div class="ll-section-sub">Generate summaries, flashcards, quizzes, and revision notes from your content.</div>
                            </div>
                        </div>
                        """)
                        with gr.Row():
                            sum_btn = gr.Button("Chapter Summary", elem_classes="ll-tool-btn")
                            quiz_btn = gr.Button("Generate Quiz", elem_classes="ll-tool-btn")
                        
                        with gr.Row(elem_classes="ll-section-header"):
                            topic_input = gr.Textbox(placeholder="Enter topic name for revision notes (e.g. Backpropagation)...", show_label=False, container=False, scale=3)
                            notes_btn = gr.Button("Revision Notes", elem_classes="ll-tool-btn", scale=1)
                            
                        tool_output = gr.Markdown("", elem_classes="ll-document-output", visible=False)

                        sum_btn.click(fn=get_summary, inputs=[course_dropdown], outputs=[tool_output])
                        quiz_btn.click(fn=run_quiz, inputs=[course_dropdown], outputs=[tool_output])
                        notes_btn.click(fn=run_notes, inputs=[course_dropdown, topic_input], outputs=[tool_output])

                    # ── Tab 5: Insights ───────────────────────────
                    with gr.Tab("Insights") as insights_tab:
                        dash_outputs, fetch_data, dash_refresh_btn = render_dashboard(analytics_tracker)
                        dash_refresh_btn.click(fn=fetch_data, inputs=[course_dropdown], outputs=dash_outputs)
                        course_dropdown.change(fn=fetch_data, inputs=[course_dropdown], outputs=dash_outputs)
                        insights_tab.select(fn=fetch_data, inputs=[course_dropdown], outputs=dash_outputs)

        # ── Event Wiring ─────────────────────────────────────────
        app.load(fn=update_library_view, outputs=[course_dropdown, library_display, library_checkboxes], show_progress="hidden")
        refresh_btn.click(fn=update_library_view, outputs=[course_dropdown, library_display, library_checkboxes], show_progress="hidden")
        upload_btn.click(
            fn=handle_upload,
            inputs=[v_upload, v_url, v_title],
            outputs=[upload_status, course_dropdown, library_display, library_checkboxes],
        )
        course_dropdown.change(fn=load_video_for_course, inputs=[course_dropdown], outputs=[course_video, right_column], show_progress="hidden")
        course_dropdown.change(fn=load_suggested_questions, inputs=[course_dropdown], outputs=[q_btn1, q_btn2, q_btn3], show_progress="hidden")
        delete_btn.click(fn=handle_delete, inputs=[library_checkboxes], outputs=[course_dropdown, library_display, library_checkboxes], show_progress="hidden")
        msg.submit(chat_manual, inputs=[msg, chatbot, course_dropdown], outputs=[msg, chatbot, timeline_display])
        send_btn.click(chat_manual, inputs=[msg, chatbot, course_dropdown], outputs=[msg, chatbot, timeline_display])
        
        q_btn1.click(chat_manual, inputs=[q_btn1, chatbot, course_dropdown], outputs=[msg, chatbot, timeline_display])
        q_btn2.click(chat_manual, inputs=[q_btn2, chatbot, course_dropdown], outputs=[msg, chatbot, timeline_display])
        q_btn3.click(chat_manual, inputs=[q_btn3, chatbot, course_dropdown], outputs=[msg, chatbot, timeline_display])


    return app


# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

# Create app at module level so Hugging Face Spaces can discover it
app = create_app()

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("LearnLens AI is starting...")
    logger.info("Live URL: https://huggingface.co/spaces/Omverse/rag-ai-assistant")
    logger.info("=" * 60)
    
    print("\n" + "=" * 60, flush=True)
    print("  LearnLens AI is running locally!", flush=True)
    print("  Access the app at: http://localhost:7860", flush=True)
    print("=" * 60 + "\n", flush=True)
    
    app.launch(show_error=True)
