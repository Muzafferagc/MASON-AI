"""
vad.py - Silero VAD ile GERCEK konusma-bitti algisi (istege bagli)

Neden? wakeword.py su ana kadar ham ses enerjisine (RMS esigi) bakarak
"konusuyor mu?" karari veriyordu. Bu, klavye takirtisi, kapi sesi, muzik gibi
gurultuleri konusma saniyor ve sessizligi kaba bir sayacla (N blok) bekliyordu.

Silero VAD, 16 kHz sese bakip her kucuk pencere icin "bu insan konusmasi mi?"
olasiligi (0..1) uretir. Boylece:
  - Gurultu ile konusma ayrilir (yanlis tetikleme azalir)
  - Kullanici gercekten sustugunda (nefes/duraklama degil) hizli anlasilir

KURULU DEGILSE zarifce devre disi kalir: wakeword.py otomatik olarak eski
enerji-esigi yontemine doner. Yani bu paket olmadan da MASON calisir.

Kurulum (istege bagli, tek seferlik):
    pip install silero-vad onnxruntime
"""

# --- Istege bagli bagimliliklar: yoksa VAD kapali ---
try:
    import numpy as np
    import torch  # silero-vad modeli torch tabanlidir
    from silero_vad import load_silero_vad
    VAD_AVAILABLE = True
except Exception:
    VAD_AVAILABLE = False

SAMPLE_RATE = 16000
# Silero v5, 16 kHz'de TAM 512 orneklik (32 ms) pencereler bekler.
WINDOW = 512


class SileroVAD:
    """Silero VAD sarmalayici. Bir ses blogu icin en yuksek konusma olasiligini
    hesaplar ve esikle karsilastirir.

    Not: Model bir kez yuklenir (ilk cagride ~1-2 MB, tek seferlik indirme) ve
    hafizada kalir. CPU'da milisaniyeler surer; ses dongusunu yavaslatmaz."""

    def __init__(self, threshold: float = 0.5):
        # onnx=False -> torch surumu (en yaygin ve kararli API). Kurulumda
        # onnxruntime varsa silero yine hizli calisir.
        self._model = load_silero_vad()
        self.threshold = float(threshold)

    def max_speech_prob(self, block) -> float:
        """block: float32 ses (herhangi uzunlukta). 512'lik pencerelere bolup
        her birinin konusma olasiligini hesaplar, en yukseğini dondurur."""
        audio = np.asarray(block, dtype="float32").flatten()
        if audio.size < WINDOW:
            return 0.0
        best = 0.0
        # Her blok icin durumu sifirla: blok-basi bagimsiz, kararli bir olcum.
        try:
            self._model.reset_states()
        except Exception:
            pass
        for i in range(0, audio.size - WINDOW + 1, WINDOW):
            chunk = torch.from_numpy(audio[i:i + WINDOW])
            try:
                p = float(self._model(chunk, SAMPLE_RATE).item())
            except Exception:
                # Herhangi bir cizik: bu blogu "konusma degil" say, dongu olmesin
                p = 0.0
            if p > best:
                best = p
        return best

    def is_speech(self, block) -> bool:
        """Bu blokta konusma var mi? (olasilik >= esik)"""
        return self.max_speech_prob(block) >= self.threshold


def try_create(config: dict):
    """Ayar acikça ve paket kuruluysa bir SileroVAD dondurur; aksi halde None.
    wakeword.py bunu cagirir: None gelirse enerji-esigi yontemine devam eder."""
    if not VAD_AVAILABLE:
        return None
    if not config.get("vad_enabled", True):
        return None
    try:
        return SileroVAD(config.get("vad_threshold", 0.5))
    except Exception:
        return None
