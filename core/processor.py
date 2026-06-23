import os
import subprocess
from faster_whisper import WhisperModel
from core.config import SESSIONS_DIR, WHISPER_MODEL

def extract_audio(video_path: str, session_id: str, video_id: str) -> str:
    """Extracts MP3 from MP4 using ffmpeg subprocess."""
    session_audio_dir = os.path.join(SESSIONS_DIR, session_id, "audio")
    os.makedirs(session_audio_dir, exist_ok=True)
    
    audio_path = os.path.join(session_audio_dir, f"{video_id}.mp3")
    
    # Run ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "128k", "-y", audio_path],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}") from e
    
    return audio_path

def transcribe_audio(audio_path: str, video_title: str) -> dict:
    """Transcribes audio using faster-whisper and returns timestamped chunks."""
    print(f"Loading faster-whisper model: {WHISPER_MODEL}")
    # Default to CPU with int8 to ensure it runs anywhere for free
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    
    print(f"Transcribing {audio_path}...")
    segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=False, task="translate")
    
    chunks = []
    full_text = []
    
    for segment in segments:
        chunks.append({
            "title": video_title,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })
        full_text.append(segment.text.strip())
        
    print(f"Transcription complete. Generated {len(chunks)} segments.")
        
    return {
        "chunks": chunks,
        "text": " ".join(full_text)
    }

def process_video_pipeline(video_path: str, session_id: str, video_id: str, video_title: str) -> dict:
    """Full pipeline: Video -> Audio -> Transcript"""
    audio_path = extract_audio(video_path, session_id, video_id)
    transcript_data = transcribe_audio(audio_path, video_title)
    return transcript_data
