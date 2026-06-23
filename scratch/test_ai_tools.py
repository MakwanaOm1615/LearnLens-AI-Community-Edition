import os
import sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(r"d:\Desktop\DATA SCIENCE\Projects\RAG-Based-AI")

from storage.course_library import CourseLibrary
from providers.embedding_provider import BAAIEmbeddingProvider
from providers.vector_store_provider import ChromaDBProvider
from providers.llm_provider import OllamaLLMProvider, GeminiLLMProvider
from processors.retriever import CourseRetriever
from processors.ai_tools import AITools

from dotenv import load_dotenv
load_dotenv()

library = CourseLibrary()
embedding_provider = BAAIEmbeddingProvider()
vector_store = ChromaDBProvider(embedding_provider)
if os.getenv("GOOGLE_API_KEY"):
    llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"))
else:
    llm_provider = OllamaLLMProvider(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model_name="llama3.2",
    )
retriever = CourseRetriever(vector_store)
ai_tools = AITools(llm_provider, retriever)

courses = library.get_all_courses()
if not courses:
    print("No courses found.")
else:
    for c in courses:
        print(f"Course: {c.title} (ID: {c.course_id})")
        print("Summary:")
        print(ai_tools.generate_summary(c.course_id))
        print("Quiz:")
        print(ai_tools.generate_quiz(c.course_id))
        break
