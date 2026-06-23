import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from core.config import GOOGLE_API_KEY, OLLAMA_BASE_URL, LLM_MODEL_LOCAL, TOP_K_RETRIEVAL
from core.vector_store import get_vector_store

def get_llm():
    """Returns Gemini if API key is set, otherwise falls back to local Ollama."""
    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)
    else:
        return Ollama(base_url=OLLAMA_BASE_URL, model=LLM_MODEL_LOCAL)

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an AI Course Assistant. Answer the user's question based ONLY on the provided course transcript excerpts.

Context Excerpts:
{context}

---

User Question: {question}

Instructions:
- Be incredibly helpful and clear.
- Base your entire answer strictly on the provided context.
- IMPORTANT: When providing facts, cite the video title and exact timestamp in MM:SS format in parentheses. Example: "The instructor states that CSS is cascading (Intro to CSS, 01:25)".
- If you cannot find the answer in the context, politely say that the information is not in the course videos.

Answer:"""
)

def format_context(docs):
    formatted = []
    for doc in docs:
        mins, secs = divmod(int(doc.metadata["start"]), 60)
        timestamp = f"{mins:02d}:{secs:02d}"
        formatted.append(f"[{doc.metadata['title']} @ {timestamp}]\n{doc.page_content}")
    return "\n\n".join(formatted)

def format_sources(docs):
    sources = []
    for doc in docs:
        mins, secs = divmod(int(doc.metadata["start"]), 60)
        timestamp = f"{mins:02d}:{secs:02d}"
        sources.append({
            "title": doc.metadata["title"],
            "timestamp": timestamp,
            "text": doc.page_content[:150] + "..."
        })
    return sources

def generate_answer(session_id: str, question: str) -> dict:
    """Retrieves context and generates an answer using LangChain."""
    vector_store = get_vector_store(session_id)
    if not vector_store:
        return {
            "answer": "No course videos have been uploaded to this session yet. Please upload a video first.",
            "sources": []
        }
        
    retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K_RETRIEVAL})
    docs = retriever.invoke(question)
    
    if not docs:
        return {
            "answer": "I couldn't find any relevant information in the uploaded course videos.",
            "sources": []
        }
        
    context_str = format_context(docs)
    prompt = prompt_template.format(context=context_str, question=question)
    
    llm = get_llm()
    try:
        response = llm.invoke(prompt)
        if hasattr(response, "content"):
            answer = response.content
        else:
            answer = str(response)
    except Exception as e:
        answer = f"Error generating answer: {str(e)}"
        
    return {
        "answer": answer,
        "sources": format_sources(docs)
    }
