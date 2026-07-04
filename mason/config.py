"""
config.py - Ayar yonetimi
Ayarlar proje klasorundeki config.json dosyasinda tutulur.
"""
import json
from pathlib import Path

# Proje ana klasoru (run.py'nin oldugu yer)
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
DB_FILE = BASE_DIR / "mason.db"

# Varsayilan ayarlar
DEFAULTS = {
    "provider": "gemini",            # "gemini" veya "ollama"
    "gemini_api_key": "",            # https://aistudio.google.com adresinden ucretsiz alinir
    "gemini_model": "gemini-2.5-flash",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2",
    "user_name": "Muzaffer",
    # Faz 1.5 - anlamsal hafiza (embeddings)
    "gemini_embedding_model": "gemini-embedding-001",
    "ollama_embedding_model": "nomic-embed-text",
    # Faz 2 - ses
    "whisper_model": "small",              # tiny / base / small / medium
    "tts_voice": "tr-TR-AhmetNeural",      # edge-tts ses adi (dogal Turkce erkek)
    "tts_rate": "+22%",                    # okuma hizi (-50% ... +100%)
    "stt_language": "tr",                  # ses tanima dili: tr / en / auto
    "voice_replies": True,                 # Mason cevaplari sesli okusun mu
    # Faz 3 - "Hey Mason" wake word
    "wake_word_enabled": True,             # arka planda "hey mason" dinlensin mi
    "clap_enabled": True,                  # cift alkisla uyanma acik mi
    "start_hidden": True,                  # uygulama gizli (tepside) baslasin mi
    # Guvenlik & gorunum
    "memory_password": "",                 # bos degilse: hafiza silmek sifre ister
    "theme": "cyan",                       # arayuz renk paleti (cyan/gold/green/violet/crimson)
}


def load_config() -> dict:
    """Ayarlari yukler; dosya yoksa varsayilanlarla olusturur."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # Eksik anahtarlari varsayilanlarla tamamla
            return {**DEFAULTS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    save_config(DEFAULTS)
    return dict(DEFAULTS)


def save_config(config: dict) -> None:
    """Ayarlari config.json dosyasina kaydeder."""
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
