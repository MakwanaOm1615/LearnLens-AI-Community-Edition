import os
import json
from models.analytics_models import CourseAnalytics
from dataclasses import asdict

class AnalyticsStorage:
    """Handles persistence of CourseAnalytics data."""
    def __init__(self, analytics_dir: str = "data/analytics"):
        self.analytics_dir = analytics_dir
        os.makedirs(self.analytics_dir, exist_ok=True)
        
    def _get_course_file(self, course_id: str) -> str:
        course_dir = os.path.join(self.analytics_dir, course_id)
        os.makedirs(course_dir, exist_ok=True)
        return os.path.join(course_dir, "progress.json")
        
    def get_analytics(self, course_id: str) -> CourseAnalytics:
        file_path = self._get_course_file(course_id)
        if not os.path.exists(file_path):
            return CourseAnalytics(course_id=course_id)
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return CourseAnalytics(**data)
            
    def save_analytics(self, analytics: CourseAnalytics):
        file_path = self._get_course_file(analytics.course_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(analytics), f, indent=2)
