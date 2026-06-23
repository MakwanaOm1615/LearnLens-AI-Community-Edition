from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid

@dataclass
class Chunk:
    """A segment of a transcript."""
    text: str
    start: float
    end: float
    title: str
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    speaker: Optional[str] = None

@dataclass
class Transcript:
    """The single source of truth for a transcribed video."""
    chunks: List[Chunk]
    full_text: str

@dataclass
class Course:
    """Metadata for an uploaded course video."""
    course_id: str
    title: str
    original_video_path: str
    duration_seconds: float = 0.0
    upload_date: str = field(default_factory=lambda: datetime.now().isoformat())
    transcript_status: str = "pending" # pending, processing, completed, failed
    embedding_status: str = "pending"
    num_chunks: int = 0
    language: str = "en"
