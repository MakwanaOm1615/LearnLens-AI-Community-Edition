from core.generation import get_llm
from core.vector_store import get_vector_store

def generate_course_summary(session_id: str) -> str:
    """Generates a high-level summary of all uploaded course videos."""
    vector_store = get_vector_store(session_id)
    if not vector_store:
        return "No videos uploaded yet."
        
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    docs = retriever.invoke("What are the main topics, overview, and summary of this course?")
    
    context = "\n".join([doc.page_content for doc in docs])
    prompt = f"Based on the following excerpts from a course, provide a comprehensive summary of what the course covers.\n\nExcerpts:\n{context}\n\nSummary:"
    
    llm = get_llm()
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        return f"Error: {e}"

def generate_flashcards(session_id: str) -> str:
    """Generates flashcards from the course content."""
    vector_store = get_vector_store(session_id)
    if not vector_store:
        return "No videos uploaded yet."
        
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    docs = retriever.invoke("Key concepts, definitions, important facts, flashcard material")
    
    context = "\n".join([doc.page_content for doc in docs])
    prompt = f"Create 5 educational flashcards based on the following course excerpts. Format them as Q: [Question] \n A: [Answer]\n\nExcerpts:\n{context}\n\nFlashcards:"
    
    llm = get_llm()
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        return f"Error: {e}"
