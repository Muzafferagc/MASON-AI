"""
llm.py - LLM saglayici katmani (Mason'un beyni)
Iki motor desteklenir:
  1. Gemini API  - Google'in ucretsiz kotali bulut modeli (varsayilan)
  2. Ollama      - bilgisayarinda tamamen yerel/ucretsiz calisan modeller
Ikisi de ayni arayuzu kullanir: chat(system_prompt, messages) -> str
"""
import requests


class LLMError(Exception):
    """LLM cagrisi basarisiz oldugunda firlatilir; mesaj kullaniciya gosterilir."""


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
        if not self.api_key:
            raise LLMError(
                "Gemini API anahtari ayarlanmamis. Sag ustteki ayarlar (⚙) "
                "bolumunden anahtarini gir. Ucretsiz anahtar: https://aistudio.google.com"
            )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        # Gemini formati: role "user" veya "model"
        contents = [
            {
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
        }
        try:
            resp = requests.post(url, json=body, timeout=120)
        except requests.RequestException as e:
            raise LLMError(f"Gemini'ye baglanilamadi: {e}") from e
        if resp.status_code != 200:
            raise LLMError(
                f"Gemini hatasi (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Gemini beklenmedik cevap dondurdu: {str(data)[:300]}") from e


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
        chat_messages = [{"role": "system", "content": system_prompt}] + [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": chat_messages, "stream": False},
                timeout=300,
            )
        except requests.RequestException as e:
            raise LLMError(
                f"Ollama'ya baglanilamadi ({self.base_url}). "
                f"Ollama kurulu ve calisiyor mu? (ollama.com) Hata: {e}"
            ) from e
        if resp.status_code != 200:
            raise LLMError(f"Ollama hatasi (HTTP {resp.status_code}): {resp.text[:300]}")
        return resp.json()["message"]["content"]


def get_provider(config: dict):
    """Ayarlara gore dogru LLM saglayicisini dondurur."""
    if config.get("provider") == "ollama":
        return OllamaProvider(config["ollama_url"], config["ollama_model"])
    return GeminiProvider(config["gemini_api_key"], config["gemini_model"])
