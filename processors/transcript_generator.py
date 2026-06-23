import os
import subprocess
import json
from faster_whisper import WhisperModel
from models.data_models import Course, Chunk, Transcript
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

class TranscriptGenerator:
    """Module 2: Processing Pipeline (Video & Documents)"""
    def __init__(self, whisper_model: str = "base"):
        self.whisper_model = whisper_model
        
    def extract_audio(self, video_path: str, output_audio_path: str) -> str:
        """Extracts MP3 from MP4."""
        try:
            subprocess.run(
                ["ffmpeg", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "128k", "-y", output_audio_path],
                check=True,
                capture_output=True
            )
            return output_audio_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}") from e

    def generate_video_transcript(self, audio_path: str, course: Course) -> Transcript:
        """Transcribes audio and preserves timestamps."""
        model = WhisperModel(self.whisper_model, device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=False, task="translate")
        
        chunks = []
        full_text = []
        
        for segment in segments:
            chunk = Chunk(
                text=segment.text.strip(),
                start=segment.start,
                end=segment.end,
                title=course.title
            )
            chunks.append(chunk)
            full_text.append(chunk.text)
            
        return Transcript(chunks=chunks, full_text=" ".join(full_text))

    def generate_document_transcript(self, file_path: str, course: Course, loader_cls) -> Transcript:
        """Extracts text from a document and creates a pseudo-transcript."""
        loader = loader_cls(file_path)
        pages = loader.load()
        
        chunks = []
        full_text = []
        
        # We assign a fake start/end time based on the page number just so the chunker doesn't crash.
        # But really the start/end is meaningless for documents.
        for i, page in enumerate(pages):
            text = page.page_content.strip()
            if not text: continue
            
            chunk = Chunk(
                text=text,
                start=float(i),
                end=float(i+1),
                title=course.title
            )
            chunks.append(chunk)
            full_text.append(text)
            
        return Transcript(chunks=chunks, full_text=" ".join(full_text))

    def save_transcript(self, transcript: Transcript, output_json_path: str):
        """Saves transcript as JSON (Single Source of Truth)."""
        data = {
            "full_text": transcript.full_text,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "start": c.start,
                    "end": c.end,
                    "title": c.title,
                    "speaker": c.speaker
                }
                for c in transcript.chunks
            ]
        }
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def process_course(self, course: Course) -> Transcript:
        """Main orchestrator for a course processing."""
        input_path = course.original_video_path
        ext = os.path.splitext(input_path)[1].lower()
        
        course_dir = os.path.dirname(input_path)
        transcript_path = os.path.join(course_dir, "transcript.json")
        
        # If we already have a transcript (e.g. from previous run), just load it!
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                chunks = [Chunk(**c) for c in data["chunks"]]
                course.transcript_status = "completed"
                return Transcript(chunks=chunks, full_text=data["full_text"])
                
        # Generate new based on type
        if ext == ".mp4":
            audio_path = os.path.join(course_dir, "audio.mp3")
            self.extract_audio(input_path, audio_path)
            transcript = self.generate_video_transcript(audio_path, course)
        elif ext == ".pdf":
            transcript = self.generate_document_transcript(input_path, course, PyPDFLoader)
        elif ext in [".docx", ".doc"]:
            transcript = self.generate_document_transcript(input_path, course, Docx2txtLoader)
        elif ext == ".txt":
            transcript = self.generate_document_transcript(input_path, course, TextLoader)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
            
        self.save_transcript(transcript, transcript_path)
        course.transcript_status = "completed"
        return transcript
