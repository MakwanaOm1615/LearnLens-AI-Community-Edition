import os
import json
from typing import List
from models.data_models import Course

class CourseLibrary:
    """Module 9: Course Library Storage"""
    def __init__(self, metadata_dir: str = "data/library"):
        self.metadata_dir = metadata_dir
        os.makedirs(self.metadata_dir, exist_ok=True)
        self.index_file = os.path.join(self.metadata_dir, "library_index.json")
        self._ensure_index()

    def _ensure_index(self):
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def save_course(self, course: Course):
        with open(self.index_file, "r", encoding="utf-8") as f:
            library = json.load(f)
            
        library[course.course_id] = course.__dict__
        
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(library, f, indent=2)

    def get_course(self, course_id: str) -> Course:
        with open(self.index_file, "r", encoding="utf-8") as f:
            library = json.load(f)
        data = library.get(course_id)
        if not data:
            raise ValueError(f"Course {course_id} not found.")
        return Course(**data)

    def get_all_courses(self) -> List[Course]:
        with open(self.index_file, "r", encoding="utf-8") as f:
            library = json.load(f)
        return [Course(**data) for data in library.values()]

    def delete_course(self, course_id: str):
        with open(self.index_file, "r", encoding="utf-8") as f:
            library = json.load(f)
            
        if course_id in library:
            del library[course_id]
            
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(library, f, indent=2)
            
        course_dir = os.path.join("data", "courses", course_id)
        if os.path.exists(course_dir):
            try:
                import shutil
                shutil.rmtree(course_dir)
            except Exception as e:
                print(f"Error removing folder {course_dir}: {e}")

