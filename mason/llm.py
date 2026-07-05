"""
llm.py - LLM saglayici katmani (Mason'un beyni)
Uc mod desteklenir:
  1. gemini  - Google'in ucretsiz kotali bulut modeli (kaliteli, gunluk limitli)
  2. ollama  - bilgisayarinda tamamen yerel/ucretsiz calisan modeller (sinirsiz)
  3. hybrid  - once Gemini; kota dolunca (HTTP 429) otomatik yerel Ollama'ya duser
Hepsi ayni arayuzu kullanir: chat(system_prompt, messages) -> str
"""
import re
import time

import requests


class LLMError(Exception):
    """LLM cagrisi basarisiz oldugunda firlatilir; mesaj kullaniciya gosterilir."""


class RateLimitError(LLMError):
    """Kota/limit asildi ya da model mesgul (HTTP 429/503) - gecici; yedege dusulur."""


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
        if not self.api_key:
            raise LLMError(
                "Gemini API anahtari ayarlanmamis. Sag ustteki ayarlar bolumunden "
                "anahtarini gir. Ucretsiz anahtar: https://aistudio.google.com"
            )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
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
        if resp.status_code in (429, 503):
            raise RateLimitError(
                f"Gemini gecici olarak kullanilamiyor (HTTP {resp.status_code})."
            )
        if resp.status_code != 200:
            raise LLMError(f"Gemini hatasi (HTTP {resp.status_code}): {resp.text[:300]}")
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Gemini beklenmedik cevap dondurdu: {str(data)[:300]}") from e


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "llama3.2", num_ctx: int = 8192):
        self.base_url = base_url.rstrip("/")
        self.model = model
        # ONEMLI: Ollama varsayilan baglam penceresi 2048 token'dir. MASON'un
        # sistem promptu (hafiza + gorevler + belgeler + kurallar) bundan cok
        # daha uzun oldugu icin, dusuk num_ctx promptun BASINI keser ve model
        # talimatlari goremez -> "sapitir", dedigini anlamaz. Bunu buyuterek
        # (varsayilan 8192) modelin tum baglami gormesini sagliyoruz.
        self.num_ctx = int(num_ctx or 8192)

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
        chat_messages = [{"role": "system", "content": system_prompt}] + [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": chat_messages,
                    "stream": False,
                    # model 10 dk bellekte kalsin -> ardisik sorular hizli olur
                    "keep_alive": "10m",
                    # temperature dusuk -> talimatlara daha sadik, daha az "sapitma"
                    "options": {"temperature": 0.4, "num_ctx": self.num_ctx},
                },
                timeout=300,
            )
        except requests.RequestException as e:
            raise LLMError(
                f"Ollama'ya bağlanılamadı ({self.base_url}). Ollama kurulu ve "
                f"çalışıyor mu? İndirmek için: https://ollama.com — Hata: {e}"
            ) from e
        if resp.status_code == 404 or (
            resp.status_code != 200 and "not found" in resp.text.lower()
        ):
            raise LLMError(
                f"'{self.model}' modeli Ollama'da yüklü değil. Terminalde şunu "
                f"çalıştır: ollama pull {self.model}"
            )
        if resp.status_code in (429, 503):
            raise RateLimitError(
                f"Ollama şu an meşgul (HTTP {resp.status_code}). Birazdan tekrar dene."
            )
        if resp.status_code != 200:
            raise LLMError(f"Ollama hatası (HTTP {resp.status_code}): {resp.text[:300]}")
        try:
            content = resp.json()["message"]["content"]
        except (KeyError, ValueError) as e:
            raise LLMError(
                f"Ollama beklenmedik cevap döndürdü: {resp.text[:300]}"
            ) from e
        # Bazi "dusunen" modeller (deepseek-r1 vb.) <think>...</think> blogu ekler
        return _strip_think(content)


def _strip_think(text: str) -> str:
    """Dusunen modellerin <think>...</think> ic monologunu cevaptan temizler."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def ollama_status(base_url: str = "http://localhost:11434") -> dict:
    """Ollama sunucusunun durumunu ve yuklu modelleri dondurur.
    UI'daki 'Bağlantıyı Test Et' butonu bunu kullanir."""
    base = (base_url or "http://localhost:11434").rstrip("/")
    try:
        resp = requests.get(f"{base}/api/tags", timeout=5)
    except requests.RequestException:
        return {"running": False, "models": []}
    if resp.status_code != 200:
        return {"running": False, "models": []}
    try:
        models = [m["name"] for m in resp.json().get("models", [])]
    except (KeyError, ValueError):
        models = []
    return {"running": True, "models": models}


class HybridProvider:
    """
    Once birincil saglayici (Gemini) denenir. Kota/limit hatasi (429/503) ya da
    baglanti hatasi olursa yedek saglayiciya (yerel Ollama) duser. Limite
    takildiktan sonra 'cooldown' suresince dogrudan yedek kullanilir; sure
    dolunca birincil tekrar denenir.
    """

    def __init__(self, primary, fallback, cooldown_seconds: int = 900):
        self.primary = primary
        self.fallback = fallback
        self.cooldown_seconds = cooldown_seconds
        self._primary_blocked_until = 0.0

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
        if time.time() < self._primary_blocked_until:
            return self.fallback.chat(system_prompt, messages)
        try:
            return self.primary.chat(system_prompt, messages)
        except RateLimitError:
            self._primary_blocked_until = time.time() + self.cooldown_seconds
            return self.fallback.chat(system_prompt, messages)
        except LLMError:
            self._primary_blocked_until = time.time() + 60
            return self.fallback.chat(system_prompt, messages)


def get_provider(config: dict):
    """Ayarlara gore dogru LLM saglayicisini dondurur."""
    provider = config.get("provider", "gemini")
    num_ctx = int(config.get("ollama_num_ctx", 8192))
    if provider == "ollama":
        return OllamaProvider(config["ollama_url"], config["ollama_model"], num_ctx)
    if provider == "hybrid":
        primary = GeminiProvider(config["gemini_api_key"], config["gemini_model"])
        fallback = OllamaProvider(config["ollama_url"], config["ollama_model"], num_ctx)
        return HybridProvider(primary, fallback, int(config.get("hybrid_cooldown_sec", 900)))
    return GeminiProvider(config["gemini_api_key"], config["gemini_model"])
