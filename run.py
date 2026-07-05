"""
MASON AI - baslatma dosyasi
Calistirmak icin:  python run.py   (konsolsuz: pythonw run.py)

Argumanlar:
    --show   Pencereyi gizli baslatma ayarina ragmen goster (masaustu "Ac" simgesi).
"""
import json
import socket
import sys
import threading
import time
from pathlib import Path

import webview

from mason import agent, memory, planner, reminders, voice, wakeword
from mason.config import load_config, save_config
from mason.database import get_conn

BASE_DIR = Path(__file__).resolve().parent
UI_FILE = BASE_DIR / "ui" / "index.html"
BACKUP_DIR = BASE_DIR / "yedekler"       # hafiza yedeklerinin (JSON) tutuldugu klasor
SHOW_FLAG = BASE_DIR / ".show.trigger"   # arka plandaki ornegi one getirme sinyali
LOCK_PORT = 50573                         # tek ornek kilidi (localhost)

window = None            # ana pencere (webview)
tray_icon = None         # sistem tepsisi ikonu (pystray)
listener = None          # wake word dinleyici (barge-in icin erisim gerek)
_lock_sock = None        # tek ornek kilidi soketi (acik kalmali)
_force_show = False      # --show ile baslatildiysa gizleme ayarini yok say
_speaking_until = 0.0    # Mason konusurken kendini duymasin diye
_last_reply_text = ""    # Mason'un su an okudugu cevap (barge-in self-trigger'i engeller)


def _mark_speaking(text: str) -> None:
    """TTS suresini kabaca tahmin et; o surede wake word dinleme sustur.
    Bu sadece bir yedek tahmindir; UI ses bitince audio_ended() ile kesin
    olarak temizler (boylece susturmadan sonra wake kilitli kalmaz)."""
    global _speaking_until, _last_reply_text
    _last_reply_text = text or ""
    _speaking_until = time.time() + max(1.5, len(text) / 14)


def _is_speaking() -> bool:
    return time.time() < _speaking_until


def _speaking_text() -> str:
    return _last_reply_text


class Api:
    """JavaScript'in cagirabildigi Python fonksiyonlari (kopru)."""

    def __init__(self):
        self._recorder = voice.Recorder()

    # ---- Chat ----
    def send_message(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return {"reply": "", "actions_done": [], "error": True}
        return agent.chat(text, load_config())

    def get_history(self) -> list:
        return agent.get_history()

    def clear_chat(self) -> dict:
        """Sohbet gecmisini temizler. HAFIZA VE GOREVLER SILINMEZ."""
        with get_conn() as conn:
            conn.execute("DELETE FROM messages")
        return {"ok": True}

    def apply_delete(self, mem_ids: list = None, task_ids: list = None,
                     password: str = "") -> dict:
        """Sifre korumali silmeyi onaylar (hafiza + gorev). UI, kullanicinin
        girdigi sifreyle cagirir; sifre dogruysa verilen id'ler silinir.
        Sifre hic ayarlanmamissa bos sifreyle de calisir (manuel silme)."""
        cfg = load_config()
        real = cfg.get("memory_password", "")
        if real and (password or "") != real:
            return {"ok": False, "error": "Şifre yanlış"}
        mem_count = task_count = 0
        for i in (mem_ids or []):
            try:
                memory.forget(int(i))
                mem_count += 1
            except Exception:
                continue
        for i in (task_ids or []):
            try:
                planner.delete_task(int(i))
                task_count += 1
            except Exception:
                continue
        return {"ok": True, "mem_count": mem_count, "task_count": task_count,
                "count": mem_count + task_count}

    def apply_forget(self, ids: list, password: str = "") -> dict:
        """Eski arayuz uyumu: sadece hafiza siler."""
        return self.apply_delete(mem_ids=ids, password=password)

    def change_password(self, old: str = "", new: str = "",
                        repeat: str = "", remove: bool = False) -> dict:
        """Silme sifresini belirler/degistirir/kaldirir.
        - Ilk kez belirleme: old bos, new == repeat zorunlu.
        - Degistirme: old mevcut sifreyle eslesmeli, new == repeat.
        - Kaldirma (remove=True): old mevcut sifreyle eslesmeli."""
        cfg = load_config()
        current = cfg.get("memory_password", "")
        if current and (old or "") != current:
            return {"ok": False, "error": "Eski şifre yanlış"}
        if remove:
            cfg["memory_password"] = ""
            save_config(cfg)
            return {"ok": True, "has_password": False}
        if not new:
            return {"ok": False, "error": "Yeni şifre boş olamaz"}
        if new != repeat:
            return {"ok": False, "error": "Yeni şifreler birbiriyle uyuşmuyor"}
        cfg["memory_password"] = new
        save_config(cfg)
        return {"ok": True, "has_password": True}

    # ---- Hafiza yedekleme ----
    def export_memory(self) -> dict:
        """Tum hafizayi 'yedekler/' klasorune tarihli bir JSON dosyasi olarak yazar."""
        try:
            items = memory.export_memories()
            BACKUP_DIR.mkdir(exist_ok=True)
            fname = f"hafiza_yedek_{time.strftime('%Y%m%d_%H%M%S')}.json"
            path = BACKUP_DIR / fname
            path.write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return {"ok": True, "count": len(items), "file": fname}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def import_memory(self) -> dict:
        """'yedekler/' klasorundeki EN YENI yedek dosyasindan hafizalari geri yukler.
        Ayni icerik zaten varsa atlanir."""
        try:
            if not BACKUP_DIR.exists():
                return {"ok": False, "error": "Yedek klasörü yok"}
            backups = sorted(BACKUP_DIR.glob("hafiza_yedek_*.json"))
            if not backups:
                return {"ok": False, "error": "Yedek dosyası bulunamadı"}
            newest = backups[-1]
            items = json.loads(newest.read_text(encoding="utf-8"))
            added = memory.import_memories(items, load_config())
            return {"ok": True, "count": added, "file": newest.name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---- Hatirlaticilar ----
    def due_reminders(self) -> dict:
        """Yaklasan/geciken gorevler icin kisa hatirlatma metni (yoksa bos)."""
        try:
            return {"text": reminders.format_reminder() or ""}
        except Exception:
            return {"text": ""}

    # ---- Yan panel verileri ----
    def get_state(self) -> dict:
        return {
            "tasks": planner.list_tasks("all"),
            "memory_tree": memory.memory_tree(),
            "plans": planner.list_plans(),
        }

    def toggle_task(self, task_id: int, done: bool) -> dict:
        planner.update_task(int(task_id), status="done" if done else "open")
        return self.get_state()

    # ---- Ayarlar ----
    def get_settings(self) -> dict:
        """Ayarlari dondurur; sifrenin kendisi arayuze GONDERILMEZ,
        sadece 'var mi yok mu' bilgisi gider (has_memory_password)."""
        cfg = dict(load_config())
        cfg["has_memory_password"] = bool(cfg.get("memory_password"))
        cfg["memory_password"] = ""
        return cfg

    def save_settings(self, settings: dict) -> dict:
        cfg = load_config()
        settings = dict(settings or {})
        # Sifre yalnizca change_password ile degistirilir (double-check akisi)
        settings.pop("memory_password", None)
        settings.pop("has_memory_password", None)
        cfg.update(settings)
        save_config(cfg)
        return self.get_settings()

    def ollama_status(self, url: str = "") -> dict:
        """Ollama calisiyor mu, hangi modeller yuklu? (Ayarlar > Test butonu)
        Sohbet modeli ve embedding modeli yuklu mu diye de bakar."""
        from mason.llm import ollama_status
        cfg = load_config()
        base = (url or cfg.get("ollama_url") or "http://localhost:11434")
        st = ollama_status(base)
        chat_model = cfg.get("ollama_model", "llama3.2")
        emb_model = cfg.get("ollama_embedding_model", "nomic-embed-text")
        # "llama3.2" ile "llama3.2:latest" ayni modeldir -> iki yonlu esle
        def has(name: str) -> bool:
            return any(
                m == name or m.split(":")[0] == name or name.split(":")[0] == m
                for m in st["models"]
            )
        st["chat_model"] = chat_model
        st["chat_model_ok"] = st["running"] and has(chat_model)
        st["embed_model"] = emb_model
        st["embed_model_ok"] = st["running"] and has(emb_model)
        return st

    # ---- Ses (Faz 2) ----
    def voice_status(self) -> dict:
        st = voice.status()
        st["wake"] = wakeword.WAKEWORD_AVAILABLE and load_config().get("wake_word_enabled", True)
        return st

    def start_recording(self) -> dict:
        try:
            self._recorder.start()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop_recording(self) -> dict:
        """Kaydi durdurur ve konusmayi yaziya cevirir."""
        try:
            audio = self._recorder.stop()
            text = voice.transcribe(audio, load_config())
            return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "error": str(e), "text": ""}

    def speak(self, text: str) -> dict:
        """Metni sese cevirir; UI base64 mp3'u calar."""
        try:
            audio = voice.speak_to_base64(text, load_config())
            _mark_speaking(text)
            return {"ok": True, "audio_b64": audio}
        except Exception as e:
            return {"ok": False, "error": str(e), "audio_b64": ""}

    def audio_ended(self) -> dict:
        """UI, sesli cevap bittiginde (veya susturuldugunda) bunu cagirir.
        Boylece 'Mason konusuyor' susturmasi ANINDA kalkar ve hemen ardindan
        'hey mason' demek calisir (mute/unmute sonrasi kilit sorunu cozulur)."""
        global _speaking_until, _last_reply_text
        _speaking_until = 0.0
        _last_reply_text = ""
        return {"ok": True}


# ---------- Tek ornek (ayni anda tek MASON) ----------

def _acquire_single_instance() -> bool:
    """localhost portuna baglanarak tek ornek kilidi al. Basarisizsa
    (port dolu) baska bir MASON zaten calisiyor demektir."""
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        _lock_sock = s  # global tutulur ki uygulama boyunca acik kalsin
        return True
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        return False


# ---------- Faz 3: "Hey Mason" ----------

def _show_window() -> None:
    try:
        window.show()
        window.maximize()  # tam ekran yap (zaten buyukse islem yapmaz -> titremez)
    except Exception:
        pass


def _watch_show_trigger() -> None:
    """Arka plandaki ornek, masaustu 'Ac' simgesinden gelen sinyali bekler:
    .show.trigger dosyasi olusunca pencereyi one getir."""
    while True:
        try:
            if SHOW_FLAG.exists():
                try:
                    SHOW_FLAG.unlink()
                except Exception:
                    pass
                _show_window()
        except Exception:
            pass
        time.sleep(0.5)


def _js(code: str) -> None:
    try:
        window.evaluate_js(code)
    except Exception:
        pass


def _on_wake_only() -> None:
    """Uyandirildi (kelime veya alkis): pencereyi ac, 'Efendim?' de, komut bekle."""
    _show_window()
    _js("setState('listening')")
    try:
        audio = voice.speak_to_base64("Efendim?", load_config())
        _mark_speaking("Efendim?")
        _js(f"playB64({json.dumps(audio)})")
    except Exception:
        pass


def _on_command(text: str) -> None:
    """Sesli komut algilandi: chat'e isle, cevabi UI'a ve hoparlore gonder."""
    _show_window()
    _js(f"voiceUser({json.dumps(text)})")
    result = agent.chat(text, load_config())
    _js(f"voiceReply({json.dumps(result['reply'])}, "
        f"{json.dumps(result['actions_done'])}, {json.dumps(result['error'])}, "
        f"{json.dumps(result.get('pending_forget', []))}, "
        f"{json.dumps(result.get('pending_tasks', []))})")


def _on_wake_status(status: str) -> None:
    """Wake word dinleyicisinin durumunu arayuze bildir."""
    _js(f"setWakeStatus({json.dumps(status)})")


def _on_interrupt() -> None:
    """BARGE-IN: Mason konusurken 'hey mason' dendi -> konusmayi ANINDA kes,
    susturmayi kaldir ve tekrar dinlemeye gec."""
    global _speaking_until, _last_reply_text
    _speaking_until = 0.0
    _last_reply_text = ""
    _js("stopSpeaking()")


def _start_wake_listener() -> None:
    global listener
    cfg = load_config()
    if cfg.get("wake_word_enabled", True) and wakeword.WAKEWORD_AVAILABLE:
        listener = wakeword.WakeWordListener(
            cfg, on_wake_only=_on_wake_only, on_command=_on_command,
            is_suppressed=_is_speaking, on_status=_on_wake_status,
            on_interrupt=_on_interrupt, get_speaking_text=_speaking_text,
        )
        listener.start()
    else:
        _on_wake_status("unavailable" if not wakeword.WAKEWORD_AVAILABLE else "disabled")


# ---------- Sistem tepsisi (istege bagli: pystray + pillow) ----------

def _start_tray() -> None:
    """Tepsi ikonu: pencere kapatilinca Mason arka planda dinlemeye devam eder."""
    global tray_icon
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return  # pystray kurulu degilse tepsi yok; normal kapanma gecerli

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill=(34, 211, 238, 255))   # camgobegi daire
    d.ellipse([22, 22, 42, 42], fill=(10, 14, 20, 255))   # arc reactor merkezi

    def show(icon, item):
        _show_window()

    def quit_app(icon, item):
        icon.stop()
        try:
            window.destroy()
        except Exception:
            pass

    tray_icon = pystray.Icon(
        "mason", img, "MASON - dinliyor",
        menu=pystray.Menu(
            pystray.MenuItem("Goster", show, default=True),
            pystray.MenuItem("Kapat", quit_app),
        ),
    )
    tray_icon.run_detached()


def _on_closing():
    """Pencere kapatilirken uygulamayi kapatma; gizle ve arka planda
    'hey mason' komutunu beklemeye devam et.

    Tamamen kapatmak icin: masaustu 'MASON Kapat' simgesi veya tepsi > Kapat.
    """
    try:
        window.hide()
    except Exception:
        pass
    return False  # kapanmayi iptal et -> arka planda dinlemeye devam


def _clear_chat_on_start() -> None:
    """Her acilista temiz ekran: sohbet gecmisini sil. HAFIZA VE GOREVLER KALIR."""
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM messages")
    except Exception:
        pass


def _backfill_embeddings_in_background():
    """Eski hafizalara embedding ekler (uygulamayi yavaslatmadan)."""
    try:
        memory.backfill_embeddings(load_config())
    except Exception:
        pass


def _notify(title: str, message: str) -> None:
    """Hatirlatmayi hem sistem tepsisi bildiriminde hem de arayuzde gosterir."""
    try:
        if tray_icon is not None:
            tray_icon.notify(message, title)
    except Exception:
        pass
    _js(f"masonReminder({json.dumps(message)})")


REMINDER_INTERVAL = 30 * 60  # 30 dakikada bir kontrol


def _reminder_loop() -> None:
    """Arka planda yaklasan/geciken gorevleri periyodik kontrol eder ve
    her gorev icin gunde en fazla bir kez hatirlatir."""
    time.sleep(8)  # acilisin oturmasini bekle
    notified_today: set[str] = set()
    last_day = time.strftime("%Y-%m-%d")
    while True:
        try:
            today = time.strftime("%Y-%m-%d")
            if today != last_day:      # yeni gun -> hatirlatmalari sifirla
                notified_today.clear()
                last_day = today
            text = reminders.format_reminder()
            if text and text not in notified_today:
                _notify("MASON — Hatırlatıcı", text)
                notified_today.add(text)
        except Exception:
            pass
        time.sleep(REMINDER_INTERVAL)


def _on_started():
    """Pencere acildiktan sonra arka plan servislerini baslat."""
    try:
        window.maximize()  # tam ekran (buyutulmus) baslat
    except Exception:
        pass
    threading.Thread(target=_backfill_embeddings_in_background, daemon=True).start()
    threading.Thread(target=_watch_show_trigger, daemon=True).start()
    threading.Thread(target=_reminder_loop, daemon=True).start()
    _start_tray()
    _start_wake_listener()
    # --show verilmediyse ve ayar gizli baslat ise: tepsiye gizlen (dinlemeye devam)
    if load_config().get("start_hidden") and not _force_show:
        try:
            window.hide()
        except Exception:
            pass


if __name__ == "__main__":
    _force_show = "--show" in sys.argv

    # Zaten calisan bir MASON var mi? Varsa yeni ornek acma.
    if not _acquire_single_instance():
        # Calisiyor: --show ise arka plandaki pencereyi one getir, sonra cik.
        if _force_show:
            try:
                SHOW_FLAG.write_text("1", encoding="utf-8")
            except Exception:
                pass
        sys.exit(0)

    # Onceki oturumdan kalmis sinyal dosyasini temizle
    try:
        SHOW_FLAG.unlink()
    except Exception:
        pass

    _clear_chat_on_start()  # temiz ekranla basla

    window = webview.create_window(
        title="MASON",
        url=str(UI_FILE),
        js_api=Api(),
        width=1280,
        height=820,
        min_size=(900, 600),
        background_color="#04070d",
    )
    window.events.closing += _on_closing
    webview.start(_on_started)
