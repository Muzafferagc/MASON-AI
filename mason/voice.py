"""
voice.py - Faz 2: Sesli konusma
  Kulak: sounddevice (mikrofon kaydi) + faster-whisper (ses -> yazi, yerel/ucretsiz)
  Agiz:  edge-tts (yazi -> ses, Microsoft'un ucretsiz dogal sesleri, internet ister)

Ses paketleri kurulu degilse uygulama yine calisir - sadece ses ozellikleri
kapali gorunur. Boylece "pip install" sorunlari Mason'u asla cokertmez.
"""
import asyncio
import base64
import re

# --- Istege bagli bagimliliklar: yoksa zarifce devre disi kal ---
try:
    import numpy as np
    import sounddevice as sd
    RECORDING_AVAILABLE = True
except Exception:
    RECORDING_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

try:
    import edge_tts
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

SAMPLE_RATE = 16000  # Whisper'in bekledigi ornekleme hizi
_whisper_model = None  # bir kez yuklenir, sonra hafizada kalir


def status() -> dict:
    """Hangi ses ozellikleri kullanilabilir?"""
    return {
        "stt": RECORDING_AVAILABLE and WHISPER_AVAILABLE,  # konusmayi yaziya cevirme
        "tts": TTS_AVAILABLE,                              # sesli cevap
    }


# ---------- KAYIT (mikrofon) ----------

class Recorder:
    """Mikrofon kaydini baslatip durduran basit sinif."""

    def __init__(self):
        self._frames = []
        self._stream = None

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if not RECORDING_AVAILABLE:
            raise RuntimeError("Ses kaydi icin: pip install sounddevice numpy")
        if self._stream:
            return
        self._frames = []

        def callback(indata, frame_count, time_info, status_flags):
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback
        )
        self._stream.start()

    def stop(self):
        """Kaydi durdurur ve ses verisini dondurur (numpy dizisi)."""
        if not self._stream:
            return None
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if not self._frames:
            return None
        audio = np.concatenate(self._frames, axis=0).flatten()
        self._frames = []
        return audio


# ---------- SES -> YAZI (faster-whisper) ----------

def transcribe(audio, config: dict) -> str:
    """Ses kaydini yaziya cevirir.

    Varsayilan dil Turkce'dir (stt_language: "tr") - boylece Whisper baska dil
    sanma hatasi yapmaz. Ingilizce konusmak icin ayarlardan "en" ya da
    otomatik algilama icin "auto" secilebilir.
    Not: Ilk kullanimda Whisper modeli indirilir (small ~460 MB, tek seferlik).
    """
    global _whisper_model
    if not WHISPER_AVAILABLE:
        raise RuntimeError("Ses tanima icin: pip install faster-whisper")
    if audio is None or len(audio) < SAMPLE_RATE // 4:  # < 0.25 sn ise bos say
        return ""
    if _whisper_model is None:
        _whisper_model = WhisperModel(
            config.get("whisper_model", "small"), device="cpu", compute_type="int8"
        )
    lang = config.get("stt_language", "tr")
    lang = None if lang == "auto" else lang
    segments, _info = _whisper_model.transcribe(audio, vad_filter=True, language=lang)
    return " ".join(s.text.strip() for s in segments).strip()


# ---------- YAZI -> SES (edge-tts) ----------

def _clean_for_speech(text: str) -> str:
    """Markdown isaretlerini temizler ki Mason 'yildiz yildiz' okumasin."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # kod bloklari
    text = re.sub(r"[*_#`>|]", " ", text)                     # markdown isaretleri
    text = re.sub(r"[✅🎉🧠🗑️✏️📅📋🌿🌱⚠️🔊🎤🌟]", " ", text)  # emojiler
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def speak_to_base64(text: str, config: dict) -> str:
    """Metni sese cevirir; UI'da calinmak uzere base64 mp3 dondurur."""
    if not TTS_AVAILABLE:
        raise RuntimeError("Sesli yanit icin: pip install edge-tts")
    clean = _clean_for_speech(text)
    if not clean:
        return ""
    voice = config.get("tts_voice", "en-US-AndrewMultilingualNeural")
    rate = config.get("tts_rate", "+18%")
    if not rate or rate == "0%":
        rate = "+0%"

    async def _synth() -> bytes:
        communicate = edge_tts.Communicate(clean[:3000], voice, rate=rate)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    audio_bytes = asyncio.run(_synth())
    return base64.b64encode(audio_bytes).decode("ascii")
