from abc import ABC, abstractmethod
from typing import Any
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import Ollama

class LLMProvider(ABC):
    """Abstract base class for LLMs."""
    @abstractmethod
    def get_llm(self) -> Any:
        pass

class GeminiLLMProvider(LLMProvider):
    """Gemini implementation using langchain-google-genai."""
    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        self.api_key = api_key
        self.model_name = model_name
        self._llm = None
        
    def get_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=self.api_key)
        return self._llm

class OllamaLLMProvider(LLMProvider):
    """Fallback implementation using local Ollama."""
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
        self._llm = None
        
    def get_llm(self) -> Ollama:
        if self._llm is None:
            self._llm = Ollama(base_url=self.base_url, model=self.model_name)
        return self._llm
