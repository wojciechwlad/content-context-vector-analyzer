"""Klient Ollama API do generowania embeddingów i wywołań LLM."""

import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import OLLAMA_CONFIG


class OllamaClient:
    """Klient do komunikacji z Ollama API."""

    def __init__(
        self,
        base_url: str | None = None,
        embedding_model: str | None = None,
        llm_model: str | None = None,
        timeout: int | None = None,
    ):
        """
        Inicjalizuje klienta Ollama.

        Args:
            base_url: URL serwera Ollama (default: http://localhost:11434)
            embedding_model: Model do embeddingów (default: nomic-embed-text)
            llm_model: Model LLM do sugestii (default: llama3.2)
            timeout: Timeout w sekundach
        """
        self.base_url = base_url or OLLAMA_CONFIG["base_url"]
        self.embedding_model = embedding_model or OLLAMA_CONFIG["embedding_model"]
        self.llm_model = llm_model or OLLAMA_CONFIG["llm_model"]
        self.timeout = timeout or OLLAMA_CONFIG["timeout"]
        self.client = httpx.Client(timeout=self.timeout)

    def check_connection(self) -> bool:
        """Sprawdza czy Ollama jest dostępna."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def list_models(self) -> list[str]:
        """Zwraca listę dostępnych modeli."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except httpx.RequestError:
            return []

    def has_model(self, model_name: str) -> bool:
        """Sprawdza czy model jest dostępny."""
        models = self.list_models()
        return any(model_name in m for m in models)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get_embedding(self, text: str, model: str | None = None) -> np.ndarray:
        """
        Generuje embedding dla tekstu.

        Args:
            text: Tekst do embeddingu
            model: Model (default: snowflake-arctic-embed2)

        Returns:
            numpy array z embeddingiem
        """
        model = model or self.embedding_model
        try:
            response = self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            return np.array(embedding)
        except Exception as e:
            print(f"[OLLAMA ERROR] Model: {model}, Text length: {len(text)}, Error: {e}")
            raise

    def get_batch_embeddings(
        self,
        texts: dict[str, str],
        model: str | None = None,
    ) -> dict[str, np.ndarray]:
        """
        Generuje embeddingi dla wielu tekstów.

        Args:
            texts: Słownik {nazwa: tekst}
            model: Model do użycia

        Returns:
            Słownik {nazwa: embedding}
        """
        embeddings = {}
        for name, text in texts.items():
            if text and text.strip():
                embeddings[name] = self.get_embedding(text, model)
        return embeddings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Generuje tekst przez LLM.

        Args:
            prompt: Prompt użytkownika
            model: Model LLM (default: llama3.2)
            system: System prompt
            temperature: Temperatura generowania

        Returns:
            Wygenerowany tekst
        """
        model = model or self.llm_model
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        response = self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=60.0,  # LLM może potrzebować więcej czasu
        )
        response.raise_for_status()
        return response.json()["response"]

    def close(self):
        """Zamyka klienta HTTP."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
