"""
MASON AI - baslatma dosyasi
Calistirmak icin:  python run.py   (konsolsuz: pythonw run.py)

Argumanlar:
    --show   Pencereyi gizli baslatma ayarina ragmen goster (masaustu "Ac" simgesi).
"""
import base64
import json
import re
import shutil
import socket
import sys
import threading
import time
from pathlib import Path

import webview

from mason import (agent, briefing, chats, documents, ics_export, memory,
                   planner, reminders, voice, wakeword, weather)
from mason.config import load_config, save_config
from mason.database import get_conn

BASE_DIR = Path(__file__).resolve().parent
UI_FILE = BASE_DIR / "ui" / "index.html"
BACKUP_DIR = BASE_DIR / "yedekler"       # hafiza yedeklerinin (JSON) tutuldugu klasor
DOCS_DIR = BASE_DIR / "belgeler"         # yuklenen dosyalarin kopyalandigi klasor
EXPORT_DIR = BASE_DIR / "disari_aktar"   # .ics gibi disa aktarilan dosyalar
SHOW_FLAG = BASE_DIR / ".show.trigger"   # arka plandaki ornegi one getirme sinyali
LOCK_PORT = 50573                         # tek ornek kilidi (localhost)

window = None            # ana pencere (webview)
tray_icon = None         # sistem tepsisi ikonu (pystray)
listener = None          # wake word dinleyici (barge-in icin erisim gerek)
_lock_sock = None        # tek ornek kilidi soketi (acik kalmali)
_force_show = False      # --show ile baslatildiysa gizleme ayarini yok say
_speaking_until = 0.0    # Mason konusurken kendini duymasin diye
_last_reply_text = ""    # Mason'un su an okudugu cevap (barge-in self-trigger'i engeller)
_skip_continuous = False # uyku moduna gecerken kesintisiz dinlemeyi bir kez atla
_last_conv_over = False   # son komut sohbeti bitirdi mi? -> mikrofonu tekrar acma
_last_expects_reply = False  # Mason soru sordu mu? -> dinleme penceresini uzat


def _reopen_window_sec(cfg: dict) -> float:
    """Kesintisiz modda mikrofon ne kadar acik kalsin? Mason bir soru sorduysa
    (kullanicidan cevap bekliyor) daha uzun; normalde kisa."""
    if _last_expects_reply:
        return cfg.get("continuous_window_reply_sec", 15)
    return cfg.get("continuous_window_sec", 8)


def _continue_or_close(cfg: dict) -> None:
    """KESINTISIZ MOD karar noktasi: son komut sohbeti bitirdiyse mikrofonu
    tekrar ACMA (kapanis sesi cal, "Hey Mason" moduna don); yoksa pencereyi
    (soru bekleniyorsa uzun) yeniden ac ve dinlemeye gec."""
    if not (cfg.get("continuous_mode") and listener is not None):
        return
    try:
        if _last_conv_over:
            _js("micClosedCue()")          # "seni artik dinlemiyorum" sesi
            _js("setState('idle')")
        else:
            listener.open_command_window(_reopen_window_sec(cfg))
            _js("setState('listening')")   # setState zaten acilis sesi calar
    except Exception:
        pass


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


def _safe_name(name: str) -> str:
    """Dosya adini guvenli hale getirir (yol/karakter enjeksiyonunu onler)."""
    name = Path(name or "dosya").name
    name = re.sub(r'[^\w.\- ğüşıöçĞÜŞİÖÇ]', "_", name).strip() or "dosya"
    return name[:120]


# "Kendini kapat / uyku moduna gec" niyetini yakalayan ifadeler. Bu komut
# uygulamayi TAMAMEN kapatmaz; X'e basilmis gibi pencereyi gizler ve Mason
# arka planda "Hey Mason" demeni beklemeye devam eder. (Alt dizi eslesmesi
# kullaniyoruz ki "uyku moduna", "gizlensene" gibi ekli halleri de yakalasin.)
_SLEEP_PHRASES = (
    "kendini kapat", "uyku mod", "uykuya ge", "gizlen",
    "arka plana ge", "arka plana ge", "pencereyi kapat", "pencereyi gizle",
    "ekrandan git", "ekrandan kaybol", "ekrandan çekil", "ekrandan cekil",
    "görünmez ol", "gorunmez ol", "kendini gizle",
)


def _looks_like_sleep(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in _SLEEP_PHRASES)


def _hide_to_tray() -> None:
    """Pencereyi gizler (uygulama arka planda calismaya / dinlemeye devam eder)."""
    try:
        window.hide()
    except Exception:
        pass


def _do_sleep(text: str) -> dict:
    """'Kendini kapat' komutu: kisa bir onay ver, sonra pencereyi gizle."""
    global _skip_continuous
    _skip_continuous = True  # uyurken kesintisiz dinleme penceresini acma
    try:
        agent.save_message("user", text)
    except Exception:
        pass
    reply = ("Uyku moduna geçiyorum, efendim. Beni istediğin an "
             "\"Hey Mason\" diyerek uyandırabilirsin.")
    try:
        agent.save_message("assistant", reply)
    except Exception:
        pass
    # Cevabin ekranda gorunmesine/seslendirilmesine firsat ver, sonra gizle.
    threading.Timer(2.2, _hide_to_tray).start()
    return {"reply": reply, "actions_done": ["😴 Uyku modu — tepside dinliyorum"],
            "error": False, "sleep": True}


def _unique_path(path: Path) -> Path:
    """Ayni adli dosya varsa sonuna sayi ekleyerek benzersiz yol uretir."""
    if not path.exists():
        return path
    stem, suffix, i = path.stem, path.suffix, 1
    while True:
        cand = path.with_name(f"{stem}_{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1


class Api:
    """JavaScript'in cagirabildigi Python fonksiyonlari (kopru)."""

    def __init__(self):
        self._recorder = voice.Recorder()

    # ---- Chat ----
    def send_message(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return {"reply": "", "actions_done": [], "error": True}
        if _looks_like_sleep(text):
            return _do_sleep(text)
        return agent.chat(text, load_config())

    def get_history(self) -> list:
        return agent.get_history()

    def clear_chat(self) -> dict:
        """YENİ sohbet: mevcut sohbet KAYITLI KALIR (SOHBETLER'de görünür),
        sadece yeni bir sohbete geçilir (ekran temizlenir). Hiçbir şey silinmez."""
        agent.set_active_chat(None)
        chats.clear_empty_chats()
        return {"ok": True}

    # ---- Sohbet gecmisi (cok-sohbetli, ChatGPT/Gemini gibi) ----
    def list_chats(self) -> list:
        """Kayitli sohbetleri (en yeni once) listeler."""
        return chats.list_chats()

    def load_chat(self, chat_id: int) -> dict:
        """Eski bir sohbeti acar: aktif yapar ve mesajlarini dondurur."""
        try:
            agent.set_active_chat(int(chat_id))
            return {"ok": True, "id": int(chat_id),
                    "messages": chats.get_messages(int(chat_id))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_chat(self, chat_id: int, password: str = "") -> dict:
        """Bir sohbeti siler. Silme sifresi ayarliysa dogru sifre gerekir."""
        cfg = load_config()
        real = cfg.get("memory_password", "")
        if real and (password or "") != real:
            return {"ok": False, "error": "Şifre yanlış"}
        try:
            if agent.get_active_chat() == int(chat_id):
                agent.set_active_chat(None)  # acik sohbeti sildiysek temiz ekrana don
            chats.delete_chat(int(chat_id))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rename_chat(self, chat_id: int, title: str) -> dict:
        try:
            chats.rename_chat(int(chat_id), title)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_chats(self) -> dict:
        """Tum sohbetleri 'yedekler/' klasorune JSON olarak yazar."""
        try:
            items = chats.export_chats()
            BACKUP_DIR.mkdir(exist_ok=True)
            fname = f"sohbet_yedek_{time.strftime('%Y%m%d_%H%M%S')}.json"
            (BACKUP_DIR / fname).write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "count": len(items), "file": fname}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def import_chats(self) -> dict:
        """En yeni sohbet yedeginden sohbetleri geri yukler."""
        try:
            files = sorted(BACKUP_DIR.glob("sohbet_yedek_*.json"))
            if not files:
                return {"ok": False, "error": "Sohbet yedeği bulunamadı"}
            items = json.loads(files[-1].read_text(encoding="utf-8"))
            added = chats.import_chats(items)
            return {"ok": True, "count": added, "file": files[-1].name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apply_delete(self, mem_ids: list = None, task_ids: list = None,
                     password: str = "", plan_ids: list = None) -> dict:
        """Sifre korumali silmeyi onaylar (hafiza + gorev + plan). UI, kullanicinin
        girdigi sifreyle cagirir; sifre dogruysa verilen id'ler silinir.
        Sifre hic ayarlanmamissa bos sifreyle de calisir (manuel silme)."""
        cfg = load_config()
        real = cfg.get("memory_password", "")
        if real and (password or "") != real:
            return {"ok": False, "error": "Şifre yanlış"}
        mem_count = task_count = plan_count = 0
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
        for i in (plan_ids or []):
            try:
                planner.delete_plan(int(i))
                plan_count += 1
            except Exception:
                continue
        return {"ok": True, "mem_count": mem_count, "task_count": task_count,
                "plan_count": plan_count,
                "count": mem_count + task_count + plan_count}

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

    def list_backups(self) -> list:
        """'yedekler/' klasorundeki tum yedek dosyalarini (hem HAFIZA hem SOHBET,
        en yeni once) tur/tarih/boyut/kayit sayisiyla listeler (YEDEKLER sekmesi)."""
        out = []
        if not BACKUP_DIR.exists():
            return out
        pats = [("hafiza_yedek_*.json", "hafıza"), ("sohbet_yedek_*.json", "sohbet")]
        files = []
        for pat, kind in pats:
            for p in BACKUP_DIR.glob(pat):
                files.append((p, kind))
        files.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
        for p, kind in files:
            try:
                stt = p.stat()
                try:
                    n = len(json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    n = None
                out.append({
                    "file": p.name, "kind": kind, "count": n,
                    "size_bytes": stt.st_size,
                    "created_at": time.strftime(
                        "%Y-%m-%d %H:%M", time.localtime(stt.st_mtime)),
                })
            except Exception:
                continue
        return out

    def restore_backup(self, file: str) -> dict:
        """Bir yedek dosyasindan geri yukler. Dosya adina gore HAFIZA mi SOHBET
        mi oldugunu anlar."""
        try:
            name = Path(file or "").name
            p = BACKUP_DIR / name
            if not p.exists():
                return {"ok": False, "error": "Yedek dosyası bulunamadı"}
            items = json.loads(p.read_text(encoding="utf-8"))
            if name.startswith("sohbet_yedek_"):
                added = chats.import_chats(items)
                return {"ok": True, "count": added, "file": name, "kind": "sohbet"}
            added = memory.import_memories(items, load_config())
            return {"ok": True, "count": added, "file": name, "kind": "hafıza"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_backup(self, file: str, password: str = "") -> dict:
        """Bir yedek dosyasini siler. Silme sifresi ayarliysa dogru sifre gerekir."""
        cfg = load_config()
        real = cfg.get("memory_password", "")
        if real and (password or "") != real:
            return {"ok": False, "error": "Şifre yanlış"}
        try:
            p = BACKUP_DIR / Path(file or "").name
            if p.exists():
                p.unlink()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---- Belgeler (dosya yukleme + RAG) ----
    def upload_files(self) -> dict:
        """Yerel dosya secme penceresini acar (tum turler, coklu secim);
        secilen her dosyayi 'belgeler/' klasorune kopyalar, icerigini
        cikarip parcalayarak belge hafizasina kaydeder."""
        try:
            paths = window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=True,
                file_types=("Tüm dosyalar (*.*)",),
            )
        except Exception as e:
            return {"ok": False, "error": f"Dosya seçici açılamadı: {e}"}
        if not paths:
            return {"ok": False, "cancelled": True}
        return self._ingest_paths(list(paths))

    def upload_blob(self, name: str, content_b64: str) -> dict:
        """Surukle-birak yedegi: dosya icerigi base64 olarak gelir; diske
        yazip ayni sekilde islenir (yol alinamayan platformlar icin)."""
        try:
            raw = base64.b64decode((content_b64 or "").split(",")[-1])
        except Exception as e:
            return {"ok": False, "error": f"Dosya çözülemedi: {e}"}
        DOCS_DIR.mkdir(exist_ok=True)
        safe = _safe_name(name or "dosya")
        dest = _unique_path(DOCS_DIR / safe)
        try:
            dest.write_bytes(raw)
        except Exception as e:
            return {"ok": False, "error": f"Dosya kaydedilemedi: {e}"}
        cfg = load_config()
        res = documents.ingest(str(dest), cfg, stored_path=str(dest))
        if not res.get("ok"):
            try:
                dest.unlink()
            except OSError:
                pass
        return {"ok": bool(res.get("ok")), "results": [res],
                "added": 1 if res.get("ok") else 0}

    def _ingest_paths(self, paths: list) -> dict:
        """Verilen dosya yollarini 'belgeler/'e kopyalayip belge hafizasina isler."""
        DOCS_DIR.mkdir(exist_ok=True)
        cfg = load_config()
        results, added = [], 0
        for src in paths:
            src = str(src)
            name = Path(src).name
            if not documents.is_supported(src):
                results.append({"ok": False, "filename": name,
                                "error": f"Desteklenmeyen tür: {Path(src).suffix}"})
                continue
            dest = _unique_path(DOCS_DIR / _safe_name(name))
            try:
                shutil.copy2(src, dest)
                stored = str(dest)
            except Exception:
                stored = src  # kopyalanamazsa orijinalden oku
            res = documents.ingest(stored, cfg, stored_path=stored)
            if res.get("ok"):
                added += 1
            elif stored != src and Path(stored).exists():
                try:
                    Path(stored).unlink()
                except OSError:
                    pass
            results.append(res)
        return {"ok": added > 0, "added": added, "count": len(paths),
                "results": results}

    def list_documents(self) -> list:
        return documents.list_documents()

    def delete_document(self, doc_id: int, password: str = "") -> dict:
        """Bir belgeyi siler. Silme sifresi ayarliysa dogru sifre gerekir."""
        cfg = load_config()
        real = cfg.get("memory_password", "")
        if real and (password or "") != real:
            return {"ok": False, "error": "Şifre yanlış"}
        try:
            documents.delete_document(int(doc_id))
            return {"ok": True}
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
            "documents": documents.list_documents(),
        }

    def toggle_task(self, task_id: int, done: bool) -> dict:
        # Tekrarlayan gorev tamamlanirsa sonraki tarih otomatik olusur
        if done:
            planner.complete_task(int(task_id))
        else:
            planner.update_task(int(task_id), status="open")
        return self.get_state()

    # ---- Takvim / gorev olusturma (arayuzden) ----
    def add_task_ui(self, fields: dict) -> dict:
        """Arayuzden (takvim gunu veya '+ ekle') yeni bir gorev/hatirlatici olusturur."""
        try:
            f = fields or {}
            title = (f.get("title") or "").strip()
            if not title:
                return {"ok": False, "error": "Başlık boş olamaz"}
            tid = planner.add_task(
                title, (f.get("project") or None), f.get("priority", 3),
                (f.get("due_date") or None), (f.get("notes") or None),
                (f.get("recurrence") or "none"))
            return {"ok": True, "id": tid}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---- Detay / duzenleme paneli ----
    def update_task_details(self, task_id: int, fields: dict) -> dict:
        """Gorev detaylarini gunceller (baslik/proje/oncelik/tarih/tekrar/not/durum)."""
        try:
            f = {k: v for k, v in (fields or {}).items() if k in
                 ("title", "project", "priority", "due_date", "status", "notes",
                  "recurrence")}
            planner.update_task(int(task_id), **f)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def update_memory_details(self, memory_id: int, fields: dict) -> dict:
        """Hafiza detaylarini gunceller (icerik/kategori/proje/not)."""
        try:
            f = fields or {}
            memory.update_memory(
                int(memory_id), content=f.get("content"),
                category=f.get("category"), project=f.get("project"),
                note=f.get("note"), config=load_config())
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def update_plan_details(self, plan_id: int, fields: dict) -> dict:
        """Plan detaylarini gunceller (baslik/donem/icerik)."""
        try:
            f = fields or {}
            planner.update_plan(int(plan_id), title=f.get("title"),
                                period=f.get("period"), content=f.get("content"))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
        'hey mason' demek calisir (mute/unmute sonrasi kilit sorunu cozulur).

        KESINTISIZ KONUSMA MODU: ayar acikça ise, ses bittikten hemen sonra
        komut penceresini yeniden acariz -> kullanici 'Hey Mason' demeden
        konusmaya devam edebilir."""
        global _speaking_until, _last_reply_text, _skip_continuous
        _speaking_until = 0.0
        _last_reply_text = ""
        if _skip_continuous:
            _skip_continuous = False  # uyku sonrasi bir kez atla
            return {"ok": True}
        # Sohbet bittiyse mikrofonu tekrar acma; yoksa (soru bekleniyorsa uzun)
        # pencereyi yeniden ac. Karar _last_conv_over/_last_expects_reply'da.
        _continue_or_close(load_config())
        return {"ok": True}

    # ---- Sabah brifingi + hava durumu + takvim ----
    def get_briefing(self) -> dict:
        """Sabah brifingi metnini (ve varsa hava) dondurur — istege bagli test/goster."""
        cfg = load_config()
        try:
            return {"ok": True,
                    "text": briefing.build_briefing(cfg, cfg.get("weather_enabled", True))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def run_briefing_now(self) -> dict:
        """Brifingi HEMEN calistir: bildirim goster + (ayar acikça) sesli oku +
        sohbete ekle. 'Brifingi şimdi dene' butonu bunu kullanir."""
        try:
            _fire_briefing(load_config(), manual=True)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_weather(self) -> dict:
        """Anlik hava durumu (takvim/ayar onizlemesi icin)."""
        w = weather.get_weather(load_config())
        return {"ok": bool(w), "weather": w}

    def detect_location(self) -> dict:
        """IP'den gercek konumu bulur (Ayarlar'daki 'Konumumu algıla' butonu)."""
        loc = weather.detect_location()
        return {"ok": bool(loc), "location": loc}

    def export_ics(self) -> dict:
        """Son tarihli gorevleri .ics takvim dosyasi olarak 'disari_aktar/'
        klasorune yazar (Google/Outlook/Apple takvimine aktarilabilir)."""
        try:
            text, count = ics_export.build_ics(planner.list_tasks("all"))
            EXPORT_DIR.mkdir(exist_ok=True)
            fname = f"mason_takvim_{time.strftime('%Y%m%d_%H%M%S')}.ics"
            path = EXPORT_DIR / fname
            path.write_text(text, encoding="utf-8")
            return {"ok": True, "count": count, "file": fname, "path": str(path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


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
    """Pencereyi gizliyse gosterir ve one getirmeye calisir.

    ONEMLI: Bu fonksiyon wake-dinleyici ARKA PLAN thread'inden cagriliyor.
    pywebview'de show()/restore()/maximize() thread-guvenlidir (GUI thread'ine
    marshal edilir). ANCAK 'window.on_top = True' ozelligini arka thread'den
    degistirmek Windows/EdgeChromium'da yakalanamayan bir NATIVE cokmeye
    (uygulama sessizce kapanir) yol acar -> bu yuzden ON_TOP KULLANMIYORUZ.
    Bunun yerine one getirmeyi guvenli evaluate_js(window.focus()) ile deniyoruz."""
    try:
        window.show()
    except Exception:
        pass
    try:
        window.restore()   # simge durumundaysa (minimized) geri ac (thread-guvenli)
    except Exception:
        pass
    try:
        window.maximize()  # tam ekran (zaten buyukse titremez)
    except Exception:
        pass
    # One getirme denemesi: evaluate_js GUI thread'ine marshal edildigi icin
    # guvenlidir; native cross-thread GUI cagrisi yapmaz.
    try:
        window.evaluate_js("window.focus()")
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
    global _last_conv_over, _last_expects_reply
    # Yeni uyanma = kullanici aktif olarak konusuyor. Onceki sohbetin "bitti"
    # bayragi burada sifirlanmali; yoksa "Efendim?" sonrasi audio_ended eski
    # karari okuyup mikrofonu acmayabilir. Cevap bekledigimiz icin uzun pencere.
    _last_conv_over = False
    _last_expects_reply = True
    _show_window()
    _js("setState('listening')")
    try:
        audio = voice.speak_to_base64("Efendim?", load_config())
        _mark_speaking("Efendim?")
        _js(f"playB64({json.dumps(audio)})")
    except Exception:
        pass


def _on_command(text: str) -> None:
    """Sesli komut algilandi: chat'e isle, cevabi UI'a ve hoparlore gonder.

    DAYANIKLILIK: cevap uretimi (ozellikle yavas/hatali Ollama) bir istisna
    firlatirsa bile UI 'İŞLİYORUM'da ASLA takili kalmasin diye her durumda
    voiceReply cagrilir. Bir hata olursa kullaniciya anlasilir mesaj gider."""
    global _last_conv_over, _last_expects_reply
    _show_window()
    _js(f"voiceUser({json.dumps(text)})")
    try:
        if _looks_like_sleep(text):
            result = _do_sleep(text)  # "kendini kapat" -> onay ver, sonra gizlen
        else:
            result = agent.chat(text, load_config())
    except Exception as e:  # noqa: BLE001 - UI kilitlenmesin
        result = {"reply": f"⚠️ Bir hata oluştu: {e}", "actions_done": [],
                  "error": True}
    # Sohbet akisi kararini sakla: audio_ended() (sesli mod) ya da asagidaki
    # (sessiz mod) dali bunu okuyup mikrofonu acar/kapatir. Uyku komutu her
    # zaman sohbeti bitirir.
    _last_conv_over = bool(result.get("conversation_over")) or _looks_like_sleep(text)
    _last_expects_reply = bool(result.get("expects_reply"))
    try:
        _js(f"voiceReply({json.dumps(result.get('reply', ''))}, "
            f"{json.dumps(result.get('actions_done', []))}, "
            f"{json.dumps(result.get('error', False))}, "
            f"{json.dumps(result.get('pending_forget', []))}, "
            f"{json.dumps(result.get('pending_tasks', []))})")
    except Exception:
        pass
    # KESINTISIZ MOD: sesli yanit KAPALIYSA audio_ended tetiklenmez; kararı
    # (devam mı, kapat mı) burada verelim. Sesli mod acikken audio_ended
    # tetiklenecegi icin burada tekrar acmayiz (cift acilis olmasin).
    try:
        cfg = load_config()
        if (not cfg.get("voice_replies", True)
                and not _looks_like_sleep(text)):
            _continue_or_close(cfg)
    except Exception:
        pass


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
    """Her acilista TEMIZ EKRANLA basla ama GECMIS SILINMEZ (ChatGPT/Gemini gibi).
    Onceki sohbetler SOHBETLER sekmesinde durur; sadece yeni bir sohbete geciyoruz."""
    try:
        agent.set_active_chat(None)   # aktif sohbet yok -> ekran temiz, gecmis kalir
        chats.clear_empty_chats()     # onceki oturumlardan kalan bos sohbetleri temizle
    except Exception:
        pass


def _backfill_embeddings_in_background():
    """Eski hafizalara embedding ekler (uygulamayi yavaslatmadan)."""
    try:
        memory.backfill_embeddings(load_config())
    except Exception:
        pass


def _native_toast(title: str, message: str) -> bool:
    """Windows yerel toast bildirimi dener (plyer varsa). Basarisizsa False."""
    if not load_config().get("notify_native", True):
        return False
    try:
        from plyer import notification as _pn
        _pn.notify(title=title, message=message[:250], app_name="MASON", timeout=10)
        return True
    except Exception:
        return False


def _notify(title: str, message: str) -> None:
    """Bildirimi uc kanaldan gosterir: (1) Windows yerel toast (plyer),
    (2) sistem tepsisi balonu, (3) arayuz ici bildirim. Biri calismazsa
    digerleri devrede kalir."""
    _native_toast(title, message)
    try:
        if tray_icon is not None:
            tray_icon.notify(message[:250], title)
    except Exception:
        pass
    _js(f"masonReminder({json.dumps(message)})")


def _fire_briefing(cfg: dict, manual: bool = False) -> None:
    """Sabah brifingini sun: bildirim + (ayar acikça) sesli oku + sohbete ekle."""
    text = briefing.build_briefing(cfg, cfg.get("weather_enabled", True))
    short = briefing.build_short(cfg)
    _notify("MASON — Günün Brifingi", short)
    # Sohbete ekle (arayuz aciksa gorunsun)
    try:
        _js(f"masonBriefing({json.dumps(text)})")
    except Exception:
        pass
    # Sesli oku (ayar acikça ve TTS varsa)
    if cfg.get("briefing_speak", True):
        try:
            audio = voice.speak_to_base64(text, cfg)
            if audio:
                _mark_speaking(text)
                _js(f"playB64({json.dumps(audio)})")
        except Exception:
            pass


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


def _to_minutes(hhmm: str) -> int:
    """'HH:MM' -> gun icindeki dakika. Bozuksa -1."""
    try:
        h, m = str(hhmm)[:5].split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return -1


def _briefing_loop() -> None:
    """Her dakika kontrol eder: brifing acikça ve saati geldiyse sabah brifingini
    sunar (gunde bir kez). Uygulama gec acilirsa gece yarisi patlamamasi icin
    yalnizca hedef saatten sonraki ~2 saatlik pencere icinde tetiklenir."""
    time.sleep(12)  # acilisin oturmasini bekle
    last_briefed_day = None
    while True:
        try:
            cfg = load_config()
            if cfg.get("briefing_enabled"):
                today = time.strftime("%Y-%m-%d")
                now_min = _to_minutes(time.strftime("%H:%M"))
                target_min = _to_minutes(str(cfg.get("briefing_time", "08:00")))
                # Hedef saatten sonra, en fazla 2 saatlik yakalama penceresi
                if (target_min >= 0 and 0 <= now_min - target_min <= 120
                        and last_briefed_day != today):
                    last_briefed_day = today
                    _fire_briefing(cfg)
        except Exception:
            pass
        time.sleep(60)


def _on_started():
    """Pencere acildiktan sonra arka plan servislerini baslat."""
    try:
        window.maximize()  # tam ekran (buyutulmus) baslat
    except Exception:
        pass
    threading.Thread(target=_backfill_embeddings_in_background, daemon=True).start()
    threading.Thread(target=_watch_show_trigger, daemon=True).start()
    threading.Thread(target=_reminder_loop, daemon=True).start()
    threading.Thread(target=_briefing_loop, daemon=True).start()
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
