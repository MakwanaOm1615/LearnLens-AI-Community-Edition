import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from core.config import EMBEDDING_MODEL, VECTOR_STORES_DIR

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def create_documents_from_transcript(transcript_data: dict, chunks_per_group=5) -> list[Document]:
    """Merges consecutive whisper segments into larger chunks and converts to LangChain Documents."""
    raw_chunks = transcript_data["chunks"]
    documents = []
    
    for i in range(0, len(raw_chunks), chunks_per_group):
        group = raw_chunks[i:i+chunks_per_group]
        if not group:
            continue
            
        combined_text = " ".join(c["text"] for c in group)
        start_time = group[0]["start"]
        end_time = group[-1]["end"]
        title = group[0]["title"]
        
        doc = Document(
            page_content=combined_text,
            metadata={
                "title": title,
                "start": start_time,
                "end": end_time
            }
        )
        documents.append(doc)
        
    return documents

def get_vector_store(session_id: str):
    """Loads an existing FAISS index for a session if it exists."""
    store_path = os.path.join(VECTOR_STORES_DIR, session_id)
    if os.path.exists(os.path.join(store_path, "index.faiss")):
        return FAISS.load_local(store_path, get_embeddings(), allow_dangerous_deserialization=True)
    return None

def add_to_vector_store(session_id: str, transcript_data: dict):
    """Creates documents and adds them to a session's FAISS index."""
    documents = create_documents_from_transcript(transcript_data)
    embeddings = get_embeddings()
    
    store_path = os.path.join(VECTOR_STORES_DIR, session_id)
    
    existing_store = get_vector_store(session_id)
    if existing_store:
        existing_store.add_documents(documents)
        existing_store.save_local(store_path)
        return existing_store
    else:
        new_store = FAISS.from_documents(documents, embeddings)
        new_store.save_local(store_path)
        return new_store
