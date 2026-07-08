"""
wakeword.py - Faz 3: "Hey Mason" veya cift alkis ile uyanma

Nasil calisir?
  1. Uygulama acilir acilmaz kucuk Whisper (tiny) modeli yuklenir
     (ilk seferde ~75 MB indirilir; hazir olunca arayuzde "AKTIF" gorunur)
  2. Ilk 2 saniyede ortam gurultusu olculur -> hassasiyet otomatik ayarlanir
  3. Mikrofon surekli kucuk bloklar halinde dinlenir
  4. Konusma algilaninca yaziya cevrilir; icinde "mason" varsa uyanir
  5. CIFT ALKIS: 0.15-1.2 sn arayla iki keskin ses de Mason'u uyandirir
  6. Uyandiktan sonraki ~12 saniyede soylenen her sey dogrudan komuttur
"""
import re
import threading
import time

from . import vad  # Silero VAD (istege bagli); kurulu degilse enerji-esigine doner

try:
    import numpy as np
    import sounddevice as sd
    from faster_whisper import WhisperModel
    WAKEWORD_AVAILABLE = True
except Exception:
    WAKEWORD_AVAILABLE = False

SAMPLE_RATE = 16000
BLOCK_SIZE = 4000          # 0.25 saniyelik bloklar
MIN_THRESHOLD = 0.006      # enerji esiginin taban degeri
SILENCE_BLOCKS_END = 4     # 1 saniye sessizlik = cumle bitti
MAX_UTTERANCE_SEC = 10     # tek seferde en fazla bu kadar kayit
COMMAND_WINDOW_SEC = 12    # uyandiktan sonra komut bekleme suresi
CLAP_PEAK = 0.30           # alkis sayilacak minimum tepe siddeti
CLAP_GAP_MIN = 0.15        # iki alkis arasi minimum sure (sn)
CLAP_GAP_MAX = 1.2         # iki alkis arasi maksimum sure (sn)

# Whisper "Mason"u bazen "Meyson/Meysın/Maysın" diye yazar - hepsini yakala
WAKE_RE = re.compile(r"\b(hey[,!\s]+)?m[ae][iy]?s[aouıi]n\w*", re.IGNORECASE)


def contains_wake_word(text: str) -> bool:
    """Metinde 'mason' (veya benzer duyulan) kelime var mi?"""
    return bool(WAKE_RE.search(text or ""))


def extract_command(text: str) -> str:
    """'Hey Mason bugun ne yapmaliyim' -> 'bugun ne yapmaliyim'"""
    m = WAKE_RE.search(text or "")
    if not m:
        return (text or "").strip()
    return text[m.end():].lstrip(" ,.!?;:-")


def is_double_clap(clap_times: list, now: float) -> bool:
    """Son iki alkis uygun aralikta mi?"""
    if len(clap_times) < 2:
        return False
    gap = clap_times[-1] - clap_times[-2]
    return CLAP_GAP_MIN <= gap <= CLAP_GAP_MAX


class WakeWordListener(threading.Thread):
    """Arka planda mikrofonu dinleyen thread.

    on_wake_only(): uyandirildi (kelime/alkis), komut yok -> Mason "Efendim?" der
    on_command(text): komut algilandi -> Mason cevaplar
    is_suppressed(): True donerse dinleme atlanir (Mason konusurken kendini duymasin)
    on_status(s): durum bildirimi -> "loading" / "listening" / "error" / "unavailable"
    """

    def __init__(self, config: dict, on_wake_only, on_command,
                 is_suppressed=None, on_status=None,
                 on_interrupt=None, get_speaking_text=None):
        super().__init__(daemon=True)
        self.config = config
        self.on_wake_only = on_wake_only
        self.on_command = on_command
        self.is_suppressed = is_suppressed or (lambda: False)
        self.on_status = on_status or (lambda s: None)
        self.on_interrupt = on_interrupt or (lambda: None)
        self.get_speaking_text = get_speaking_text or (lambda: "")
        self.stop_flag = threading.Event()
        self._model = None
        self._command_mode_until = 0.0
        self._threshold = 0.012
        self._busy = False       # bir komut islenirken yeni sesleri atla
        self._busy_since = 0.0   # kilitlenmeye karsi: cok uzun surerse sifirla
        self._vad = None         # Silero VAD (run() icinde yuklenir; None=enerji)

    # --- yardimcilar ---

    def _get_model(self):
        if self._model is None:
            # Uyanma icin kucuk ve hizli "tiny" model yeterlidir
            self._model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return self._model

    def _transcribe(self, audio) -> str:
        lang = self.config.get("stt_language", "tr")
        lang = None if lang == "auto" else lang
        segments, _ = self._get_model().transcribe(audio, vad_filter=True, language=lang)
        return " ".join(s.text.strip() for s in segments).strip()

    def _wake(self) -> None:
        """Uyanma: komut penceresi ac ve 'Efendim?' de."""
        self._command_mode_until = time.time() + COMMAND_WINDOW_SEC
        self.on_wake_only()

    def open_command_window(self, seconds: float = 8.0) -> None:
        """KESINTISIZ KONUSMA MODU: 'Hey Mason' demeden komut penceresini yeniden
        acar. run.py, Mason cevabini bitirdikten (ses bittikten) sonra bunu cagirir;
        boylece kullanici dogrudan devam edebilir. Sessizlikte pencere kendiliginden
        kapanir ve normal wake-word moduna donulur."""
        self._command_mode_until = time.time() + max(2.0, float(seconds))

    def _dispatch(self, audio) -> None:
        """Konusmayi AYRI bir thread'de isle. Boylece yavas yaziya cevirme
        ve LLM cevabi ses dongusunu bloklamaz; mikrofon okunmaya devam eder
        (aksi halde ses tamponu tasar, InputStream cokerdi ve dinleme olurdu).
        Onceki komut hala islenirken gelen yeni sesler atlanir.
        GUVENLIK: bir komut (or. LLM cagrisi) takilirsa _busy sonsuza kadar
        acik kalmasin diye 25 sn sonra kilit zorla acilir."""
        if self._busy:
            if time.time() - self._busy_since < 25:
                return
            self._busy = False  # kilit cok uzun surdu -> zorla ac
        self._busy = True
        self._busy_since = time.time()

        def _work():
            try:
                self._handle_utterance(audio)
            finally:
                self._busy = False

        threading.Thread(target=_work, daemon=True).start()

    def _is_echo_of_reply(self, text: str) -> bool:
        """Duyulan ses aslinda Mason'un kendi cevabi mi (hoparlorden kaçak)?
        Cevabin kelimelerinin cogu bu metinde geciyorsa 'eko' say -> yok say."""
        reply = (self.get_speaking_text() or "").lower()
        if not reply:
            return False
        words = [w for w in re.findall(r"\w+", text.lower()) if len(w) > 2]
        if not words:
            return True
        hits = sum(1 for w in words if w in reply)
        return hits / len(words) > 0.6

    def _handle_utterance(self, audio) -> None:
        speaking = self.is_suppressed()
        text = self._transcribe(audio)
        if not text:
            return
        if speaking:
            # BARGE-IN: Mason konusurken sadece "hey mason" onu boler.
            # Kendi sesini (eko) bolmesin diye ek kontrol yapilir.
            if contains_wake_word(text) and not self._is_echo_of_reply(text):
                self.on_interrupt()   # konusmayi kes
                self._wake()          # "Efendim?" de, komut bekle
            return
        if time.time() < self._command_mode_until:
            # Zaten uyanik: soylenen sey dogrudan komuttur
            self._command_mode_until = 0.0
            self.on_command(text)
        elif contains_wake_word(text):
            command = extract_command(text)
            if len(command) > 2:
                self.on_command(command)   # "hey mason + komut" tek cumlede
            else:
                self._wake()               # sadece cagirdi -> "Efendim?"

    def _calibrate(self, stream) -> None:
        """Ilk 2 saniyede ortam gurultusunu olc, esigi ona gore ayarla."""
        energies = []
        for _ in range(8):
            block, _ = stream.read(BLOCK_SIZE)
            block = block.flatten()
            energies.append(float(np.sqrt(np.mean(block ** 2))))
        noise = sorted(energies)[len(energies) // 2]  # medyan
        self._threshold = max(MIN_THRESHOLD, noise * 3.5)

    # --- ana dongu ---

    def run(self) -> None:
        if not WAKEWORD_AVAILABLE:
            self.on_status("unavailable")
            return
        self.on_status("loading")
        try:
            self._get_model()  # modeli simdiden indir/yukle (ilk sefer uzun surer)
        except Exception:
            self.on_status("error")
            return

        # Silero VAD'i yuklemeyi dene (istege bagli). Kurulu degilse ya da ayar
        # kapaliysa None kalir; _listen_once otomatik enerji-esigine doner.
        try:
            self._vad = vad.try_create(self.config)
        except Exception:
            self._vad = None

        # KENDINI ONARAN DINLEME: mikrofon/stream cokerse thread olmesin;
        # kisa bekleyip stream'i yeniden ac. Boylece "bir komuttan sonra
        # bir daha algilamiyor" sorunu kalici olarak ortadan kalkar.
        while not self.stop_flag.is_set():
            try:
                self._listen_once()
            except Exception:
                self.on_status("error")  # mikrofon hatasi uygulamayi cokertmesin
                time.sleep(1.0)          # sonra tekrar dinlemeye basla

    def _listen_once(self) -> None:
        clap_enabled = self.config.get("clap_enabled", True)
        utterance, silence_count, in_speech = [], 0, False
        clap_times = []
        prev_peak = 0.0

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", blocksize=BLOCK_SIZE) as stream:
                self._calibrate(stream)
                self.on_status("listening")
                errors = 0
                while not self.stop_flag.is_set():
                    try:
                        block, _ = stream.read(BLOCK_SIZE)
                    except Exception:
                        # Gecici okuma hatasi (or. tampon tasmasi): dinlemeyi
                        # oldurme, kisa bekleyip devam et. Ust uste cok olursa cik.
                        errors += 1
                        if errors > 40:
                            raise
                        time.sleep(0.05)
                        continue
                    errors = 0
                    block = block.flatten()
                    energy = float(np.sqrt(np.mean(block ** 2)))
                    peak = float(np.max(np.abs(block)))

                    # --- CIFT ALKIS algilama ---
                    if clap_enabled and not self.is_suppressed():
                        # Keskin tepe + onceki blok sakin = alkis adayi
                        if peak > CLAP_PEAK and prev_peak < CLAP_PEAK * 0.5:
                            now = time.time()
                            clap_times = [t for t in clap_times if now - t < 2.0]
                            clap_times.append(now)
                            if is_double_clap(clap_times, now):
                                clap_times = []
                                utterance, in_speech, silence_count = [], False, 0
                                self._wake()
                                prev_peak = peak
                                continue
                    prev_peak = peak

                    # --- Konusma algilama ---
                    # Silero VAD kuruluysa (ve Mason konusmuyorsa) "bu blok
                    # insan konusmasi mi?" karari VAD ile verilir -> gurultuye
                    # dayanikli, sessizlik hizli anlasilir. Aksi halde ya da
                    # Mason konusurken (barge-in / eko riski) klasik enerji
                    # esigine dusulur: esigi yukseltip hoparlorden kaçan kendi
                    # sesini konusma sanmayi engelleriz, ama yuksek sesle
                    # "hey mason" dersen yine yakalar.
                    thr = self._threshold * (2.2 if self.is_suppressed() else 1.0)
                    if self._vad is not None and not self.is_suppressed():
                        # Ucuz on-kapi: tam sessizlikte VAD'i bosuna cagirma.
                        speech = energy > (self._threshold * 0.4) and \
                            self._vad.is_speech(block)
                    else:
                        speech = energy > thr

                    if speech:
                        in_speech = True
                        silence_count = 0
                        utterance.append(block)
                        if len(utterance) * BLOCK_SIZE > SAMPLE_RATE * MAX_UTTERANCE_SEC:
                            audio = np.concatenate(utterance)
                            utterance, in_speech = [], False
                            self._dispatch(audio)
                    elif in_speech:
                        silence_count += 1
                        utterance.append(block)
                        if silence_count >= SILENCE_BLOCKS_END:
                            audio = np.concatenate(utterance)
                            utterance, in_speech, silence_count = [], False, 0
                            self._dispatch(audio)
                    # sessizlikte hicbir sey yapma -> CPU bosta kalir

    def stop(self) -> None:
        self.stop_flag.set()
