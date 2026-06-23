from providers.vector_store_provider import VectorStoreProvider

class CourseRetriever:
    """Module 6: Retriever"""
    def __init__(self, vector_store: VectorStoreProvider):
        self.vector_store = vector_store
        
    def retrieve_chunks(self, course_id: str, query: str, k: int = 5):
        """
        Receives query -> Search vector db -> Returns top chunks with timestamps.
        Never sends the full transcript to the LLM.
        """
        retriever = self.vector_store.get_retriever(collection_name=course_id, k=k)
        docs = retriever.invoke(query)
        return docs
