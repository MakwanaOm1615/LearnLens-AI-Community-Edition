from abc import ABC, abstractmethod
from typing import Any
from langchain_huggingface import HuggingFaceEmbeddings

class EmbeddingProvider(ABC):
    """Abstract base class for embedding models."""
    @abstractmethod
    def get_embeddings(self) -> Any:
        pass

class BAAIEmbeddingProvider(EmbeddingProvider):
    """Implementation for BAAI/bge-small-en-v1.5 embedding model."""
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._embeddings = None
        
    def get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(model_name=self.model_name)
        return self._embeddings
