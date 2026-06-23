from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

@dataclass
class CourseAnalytics:
    """Stores progress and analytics for a specific course."""
    course_id: str
    questions_asked: int = 0
    concepts_learned: List[str] = field(default_factory=list)
    quiz_attempts: int = 0
    quiz_scores: List[float] = field(default_factory=list)
    flashcards_generated: int = 0
    study_sessions: int = 0
    time_spent_seconds: float = 0.0
    most_asked_topics: Dict[str, int] = field(default_factory=dict)
    weak_areas: List[str] = field(default_factory=list)
    strong_areas: List[str] = field(default_factory=list)
    recent_activity: List[str] = field(default_factory=list)
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
