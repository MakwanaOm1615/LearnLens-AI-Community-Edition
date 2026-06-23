from abc import ABC, abstractmethod
from typing import List, Any
from langchain_core.documents import Document
from langchain_chroma import Chroma
from providers.embedding_provider import EmbeddingProvider
import os

class VectorStoreProvider(ABC):
    """Abstract base class for Vector Databases."""
    @abstractmethod
    def add_documents(self, collection_name: str, documents: List[Document]) -> None:
        pass
        
    @abstractmethod
    def get_retriever(self, collection_name: str, k: int = 5) -> Any:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        pass

class ChromaDBProvider(VectorStoreProvider):
    """Development implementation using ChromaDB."""
    def __init__(self, embedding_provider: EmbeddingProvider, persist_directory: str = "data/vector_stores"):
        self.embedding_provider = embedding_provider
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        
    def add_documents(self, collection_name: str, documents: List[Document]) -> None:
        embeddings = self.embedding_provider.get_embeddings()
        Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )
        
    def get_retriever(self, collection_name: str, k: int = 5) -> Any:
        embeddings = self.embedding_provider.get_embeddings()
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=self.persist_directory
        )
        return vectorstore.as_retriever(search_kwargs={"k": k})

    def delete_collection(self, collection_name: str) -> None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_directory)
            client.delete_collection(collection_name)
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")

