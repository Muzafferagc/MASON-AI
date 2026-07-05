"""
embeddings.py - Anlamsal hafiza icin embedding katmani (Faz 1.5)

Embedding nedir? Bir metni, anlamini temsil eden sayilardan olusan bir
vektore cevirme islemidir. Iki metnin vektorleri birbirine ne kadar
yakinsa anlamlari da o kadar benzerdir. Boylece "okul projesi" diye
aradiginda "universite odevi" kaydi da bulunur — kelime eslesmesi degil,
ANLAM eslesmesi yapilir. Buna RAG (Retrieval-Augmented Generation) denir.

Embedding alinamazsa (internet yok, kota doldu vs.) sistem sessizce
eski yonteme (en yeni hafizalari kullanma) geri doner - uygulama asla cokmez.
"""
import math

import requests


def embed_text(text: str, config: dict) -> list[float] | None:
    """Metni embedding vektorune cevirir. Basarisiz olursa None doner."""
    try:
        provider = config.get("provider", "gemini")
        if provider == "ollama":
            return _embed_ollama(text, config)
        if provider == "hybrid":
            # Once Gemini; kota dolar/basarisiz olursa yerel Ollama'ya dus
            return _embed_gemini(text, config) or _embed_ollama(text, config)
        return _embed_gemini(text, config)
    except Exception:
        return None  # embedding olmadan da calismaya devam et


def _embed_gemini(text: str, config: dict) -> list[float] | None:
    api_key = config.get("gemini_api_key")
    if not api_key:
        return None
    model = config.get("gemini_embedding_model", "gemini-embedding-001")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:embedContent?key={api_key}"
    )
    resp = requests.post(
        url,
        json={"content": {"parts": [{"text": text[:8000]}]}},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    return resp.json()["embedding"]["values"]


def _embed_ollama(text: str, config: dict) -> list[float] | None:
    base = config.get("ollama_url", "http://localhost:11434").rstrip("/")
    model = config.get("ollama_embedding_model", "nomic-embed-text")
    resp = requests.post(
        f"{base}/api/embed",
        json={"model": model, "input": text[:8000]},
        timeout=60,
    )
    if resp.status_code != 200:
        return None
    embs = resp.json().get("embeddings")
    return embs[0] if embs else None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Iki vektorun benzerligi: 1.0 = ayni anlam, 0 = alakasiz."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
