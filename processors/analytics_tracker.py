from datetime import datetime
from storage.analytics_storage import AnalyticsStorage

class AnalyticsTracker:
    def __init__(self, storage: AnalyticsStorage):
        self.storage = storage

    def log_question_asked(self, course_id: str, concepts: list[str]):
        if not course_id: return
        analytics = self.storage.get_analytics(course_id)
        analytics.questions_asked += 1
        
        for concept in concepts:
            concept = concept.strip()
            if not concept: continue
            if concept not in analytics.concepts_learned:
                analytics.concepts_learned.append(concept)
            
            # Track most asked topics
            analytics.most_asked_topics[concept] = analytics.most_asked_topics.get(concept, 0) + 1
            
        activity = f"Asked a question involving {len(concepts)} concepts at {datetime.now().strftime('%H:%M')}"
        analytics.recent_activity.insert(0, activity)
        analytics.recent_activity = analytics.recent_activity[:10] # Keep last 10
        
        # Calculate strong/weak areas (simple heuristic based on frequency of questions asked)
        sorted_topics = sorted(analytics.most_asked_topics.items(), key=lambda item: item[1], reverse=True)
        analytics.weak_areas = [k for k, v in sorted_topics[:3]] # Most asked = needs most help
        analytics.strong_areas = [k for k, v in sorted_topics[-3:]] if len(sorted_topics) > 3 else []
        
        analytics.last_accessed = datetime.now().isoformat()
        self.storage.save_analytics(analytics)
        
    def log_flashcards_generated(self, course_id: str, count: int = 5):
        if not course_id: return
        analytics = self.storage.get_analytics(course_id)
        analytics.flashcards_generated += count
        activity = f"Generated {count} flashcards at {datetime.now().strftime('%H:%M')}"
        analytics.recent_activity.insert(0, activity)
        analytics.recent_activity = analytics.recent_activity[:10]
        self.storage.save_analytics(analytics)
