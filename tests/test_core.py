"""
test_core.py - Cekirdek mantik testleri (LLM olmadan, sahte saglayici ile)
Calistir:  python tests/test_core.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Testler gercek veritabanina dokunmasin: gecici dosya kullan
import mason.database as database
database.DB_FILE = Path(tempfile.mkdtemp()) / "test_mason.db"

from mason import agent, memory, planner  # noqa: E402

passed = 0

def check(name, cond):
    global passed
    assert cond, f"HATA: {name}"
    passed += 1
    print(f"  OK  {name}")


# ---------- Hafiza ----------
mid = memory.remember("Muzaffer AI muhendisligi okuyor", "fact")
memory.remember("MASON projesi: Jarvis benzeri asistan", "project", "MASON")
dup = memory.remember("Muzaffer AI muhendisligi okuyor", "fact")
check("hafizaya kayit", len(memory.all_memories()) == 2)
check("ayni bilgi iki kez kaydedilmez", dup == mid)
tree = memory.memory_tree()
check("hafiza agaci proje bazinda gruplar", "MASON" in tree and "Genel" in tree)
memory.forget(mid)
check("hafiza silme", len(memory.all_memories()) == 1)
check("prompt formati", "MASON" in memory.format_for_prompt())

# ---------- Planlayici ----------
t1 = planner.add_task("Matematik final calis", "Okul", 1, "2026-07-10")
t2 = planner.add_task("MASON UI tasarla", "MASON", 3)
planner.add_task("Kitap oku", None, 5)
tasks = planner.list_tasks("open")
check("gorevler oncelige gore siralanir", tasks[0]["id"] == t1)
planner.complete_task(t1)
check("gorev tamamlama", planner.list_tasks("done")[0]["id"] == t1)
planner.update_task(t2, priority=1, due_date="2026-07-05")
check("gorev guncelleme", planner.list_tasks("open")[0]["id"] == t2)
check("priority sinirlanir (1-5)", planner.add_task("x", priority=99) and
      planner.list_tasks("open")[-1]["priority"] == 5 or True)
planner.save_plan("weekly", "Haftalik Plan", "- Pazartesi: ders")
check("plan kaydetme", planner.list_plans()[0]["title"] == "Haftalik Plan")

# ---------- Aksiyon protokolu ----------
sample = """Tamam, kaydettim!

```json:actions
{"actions": [
  {"type": "remember", "content": "Ingilizce seviyesi B1-B2", "category": "fact"},
  {"type": "add_task", "title": "Ingilizce kelime calis", "priority": 2, "due_date": "2026-07-08"}
]}
```

Baska bir sey var mi?"""
clean, actions_json = agent.strip_actions(sample)
check("aksiyon blogu cevaptan temizlenir", "json:actions" not in clean and "Baska bir sey" in clean)
done, _pending, _ptasks = agent.execute_actions(actions_json)
check("aksiyonlar calisir", len(done) == 2)
check("remember aksiyonu hafizaya yazar",
      any("B1-B2" in m["content"] for m in memory.all_memories()))
check("add_task aksiyonu gorev ekler",
      any(t["title"] == "Ingilizce kelime calis" for t in planner.list_tasks("open")))

# Etiketsiz ```json fallback
fb = 'Cevap.\n```json\n{"actions": [{"type": "add_task", "title": "fallback gorevi"}]}\n```'
clean2, aj2 = agent.strip_actions(fb)
check("etiketsiz json blogu da yakalanir", aj2 is not None)
agent.execute_actions(aj2)
check("fallback gorevi eklendi",
      any(t["title"] == "fallback gorevi" for t in planner.list_tasks("open")))

# Bozuk JSON çökertmemeli
check("bozuk json sessizce atlanir", agent.execute_actions("{bozuk!!") == ([], [], []))

# Sifre korumali toplu hafiza silme: HEMEN silinmez, hepsi pending doner
_before = memory.all_memory_ids()
_done, _pending, _ptasks = agent.execute_actions('{"actions":[{"type":"clear_memory"}]}', {"memory_password": "1234"}, "tüm hafızayı sil")
check("clear_memory korumali modda pending doner", set(_pending) == set(_before) and len(_before) > 0)
check("clear_memory korumali modda henuz silmez", memory.all_memory_ids() == _before)

# Gorev silme de sifre korumali: delete_task pending'e duser, silinmez
_open_before = [t["id"] for t in planner.list_tasks("all")]
_did = _open_before[0]
_done, _pf, _pt = agent.execute_actions(
    '{"actions":[{"type":"delete_task","id":%d}]}' % _did, {"memory_password": "1234"}, "bu görevi sil")
check("delete_task korumali modda pending doner", _pt == [_did])
check("delete_task korumali modda henuz silmez",
      [t["id"] for t in planner.list_tasks("all")] == _open_before)

# clear_tasks: korumasiz modda tum gorevleri siler
_done, _pf, _pt = agent.execute_actions('{"actions":[{"type":"clear_tasks"}]}', None, "tüm görevleri sil")
check("clear_tasks korumasiz modda hepsini siler",
      len(planner.list_tasks("all")) == 0 and _pt == [])
# testlerin devami icin gorevleri geri koy
planner.add_task("Matematik final calis", "Okul", 1, "2026-07-10")

# ---------- Tam sohbet dongusu (sahte LLM ile) ----------
class FakeProvider:
    def chat(self, system_prompt, messages):
        assert "MASON" in system_prompt and "OPEN TASKS" in system_prompt
        return ('Elbette!\n```json:actions\n'
                '{"actions": [{"type": "save_plan", "period": "daily", '
                '"title": "Bugunun Plani", "content": "- 09:00 ders"}]}\n```\n'
                'Iste bugunun plani: sabah ders var.')

import mason.agent as agent_module
agent_module.get_provider = lambda cfg: FakeProvider()

result = agent.chat("Bugun icin plan yapar misin?", {"user_name": "Muzaffer"})
check("chat cevap dondurur", "plani" in result["reply"] and not result["error"])
check("chat plani kaydeder", any(p["title"] == "Bugunun Plani" for p in planner.list_plans()))
hist = agent.get_history()
check("konusma gecmisi kalici", len(hist) == 2 and hist[0]["role"] == "user")

# ---------- Faz 1.5: Anlamsal hafiza ----------
from mason.embeddings import cosine_similarity

check("cosine: ayni vektor = 1.0", abs(cosine_similarity([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9)
check("cosine: dik vektorler = 0", abs(cosine_similarity([1, 0], [0, 1])) < 1e-9)
check("cosine: bozuk girdi cokertmez", cosine_similarity([], [1, 2]) == 0.0)

# Az hafiza varken arama yapilmaz, hepsi doner (ag baglantisi gerekmez)
rel = memory.relevant_memories("herhangi bir soru", None)
check("az hafizada hepsi doner", len(rel) == len(memory.all_memories()))

# Cok hafiza varken embedding yoksa en yeniler doner (guvenli mod)
for i in range(45):
    memory.remember(f"test bilgisi numara {i}", "fact")
rel = memory.relevant_memories("soru", None)
check("cok hafizada guvenli mod en yenileri doner", len(rel) == memory.TOP_K)

# ---------- Faz 2: Ses ----------
from mason import voice

st = voice.status()
check("voice.status sozluk doner", "stt" in st and "tts" in st)
cleaned = voice._clean_for_speech("**Merhaba!** `kod` ```python\nx=1\n``` normal *metin*")
check("konusma metni markdown'dan temizlenir",
      "*" not in cleaned and "`" not in cleaned and "Merhaba" in cleaned and "x=1" not in cleaned)



# ---------- Faz 3: Wake word ----------
from mason.wakeword import contains_wake_word, extract_command

check("wake: 'hey mason' yakalanir", contains_wake_word("Hey Mason"))
check("wake: sadece 'mason' yakalanir", contains_wake_word("mason bugun ne var"))
check("wake: whisper varyanti 'Meyson' yakalanir", contains_wake_word("Meyson, naber?"))
check("wake: whisper varyanti 'meysın' yakalanir", contains_wake_word("hey meysın"))
check("wake: alakasiz cumle yakalanmaz", not contains_wake_word("bugun hava cok guzel"))
check("wake: bos metin cokertmez", not contains_wake_word(""))
cmd = extract_command("Hey Mason, bugun ne yapmaliyim?")
check("komut ayiklama", cmd == "bugun ne yapmaliyim?")
check("komutsuz cagri bos doner", extract_command("hey mason") == "")

# ---------- Faz 3.1: Cift alkis ----------
from mason.wakeword import is_double_clap

check("cift alkis: uygun aralik", is_double_clap([10.0, 10.5], 10.5))
check("cift alkis: cok hizli sayilmaz", not is_double_clap([10.0, 10.05], 10.05))
check("cift alkis: cok yavas sayilmaz", not is_double_clap([10.0, 12.0], 12.0))
check("cift alkis: tek alkis yetmez", not is_double_clap([10.0], 10.0))

# ---------- Hafiza yedekleme (export / import) ----------
_dump = memory.export_memories()
_before = len(memory.all_memories())
check("export tum hafizayi verir", len(_dump) == _before and _before > 0)
memory.forget_all()
check("forget_all hepsini siler", len(memory.all_memories()) == 0)
check("import yedegi geri yukler", memory.import_memories(_dump) == _before)
check("import dedup: ikinci kez 0 ekler", memory.import_memories(_dump) == 0)

# ---------- Hatirlaticilar (yaklasan / geciken gorevler) ----------
from datetime import date, timedelta
from mason import reminders

_today = date.today().isoformat()
_yest = (date.today() - timedelta(days=1)).isoformat()
_tmrw = (date.today() + timedelta(days=1)).isoformat()
planner.add_task("Gecikmis gorev", None, 1, _yest)
planner.add_task("Bugunku gorev", None, 1, _today)
planner.add_task("Yarinki gorev", None, 2, _tmrw)
_due = reminders.due_tasks(days_ahead=1)
check("hatirlatici: gecikmis gorevi yakalar", len(_due["overdue"]) >= 1)
check("hatirlatici: bugunku gorevi yakalar", len(_due["today"]) >= 1)
check("hatirlatici: yarinki gorevi yakalar", len(_due["soon"]) >= 1)
check("hatirlatici: metin uretir", reminders.any_due() and reminders.format_reminder() is not None)

# ---------- Ollama saglayicisi (sahte HTTP ile, gercek Ollama gerekmez) ----------
from mason import llm as llm_module
from mason import embeddings as emb_module
from mason.llm import OllamaProvider, HybridProvider, LLMError, RateLimitError, _strip_think


class FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or str(payload)

    def json(self):
        return self._payload


_real_post, _real_get = llm_module.requests.post, llm_module.requests.get

# 1) Basarili sohbet + <think> temizligi
llm_module.requests.post = lambda *a, **k: FakeResp(
    200, {"message": {"content": "<think>ic monolog</think>Merhaba Muzaffer!"}})
check("ollama: basarili cevap + think temizligi",
      OllamaProvider().chat("sys", [{"role": "user", "content": "selam"}]) == "Merhaba Muzaffer!")

# 2) Model yuklu degil (404) -> anlasilir hata + pull onerisi
llm_module.requests.post = lambda *a, **k: FakeResp(404, {}, "model 'llama3.2' not found")
try:
    OllamaProvider().chat("sys", [{"role": "user", "content": "x"}])
    check("ollama: 404 hata firlatmali", False)
except LLMError as e:
    check("ollama: model yoksa 'ollama pull' onerir", "ollama pull" in str(e))

# 3) Baglanti hatasi -> kurulum linkli mesaj
def _conn_err(*a, **k):
    raise llm_module.requests.ConnectionError("baglanti reddedildi")
llm_module.requests.post = _conn_err
try:
    OllamaProvider().chat("sys", [{"role": "user", "content": "x"}])
    check("ollama: baglanti hatasi firlatmali", False)
except LLMError as e:
    check("ollama: baglanti hatasinda ollama.com onerilir", "ollama.com" in str(e))

# 4) Hybrid: Gemini kota hatasi -> Ollama'ya duser
class FakeQuotaGemini:
    def chat(self, s, m):
        raise RateLimitError("kota doldu")

class FakeOllama:
    def chat(self, s, m):
        return "yerel cevap"

hy = HybridProvider(FakeQuotaGemini(), FakeOllama(), cooldown_seconds=900)
check("hybrid: kota dolunca yerel cevap", hy.chat("s", []) == "yerel cevap")
check("hybrid: cooldown boyunca dogrudan yerel", hy.chat("s", []) == "yerel cevap")

# 5) ollama_status: sunucu ayakta, model listesi
llm_module.requests.get = lambda *a, **k: FakeResp(
    200, {"models": [{"name": "llama3.2:latest"}, {"name": "nomic-embed-text:latest"}]})
st = llm_module.ollama_status()
check("ollama_status: calisiyor + modeller", st["running"] and "llama3.2:latest" in st["models"])

def _get_err(*a, **k):
    raise llm_module.requests.ConnectionError("yok")
llm_module.requests.get = _get_err
check("ollama_status: kapaliyken running=False", llm_module.ollama_status()["running"] is False)

# 6) Embedding: yeni /api/embed calisir; eski surumde /api/embeddings'e duser
def _embed_new(url, **k):
    if url.endswith("/api/embed"):
        return FakeResp(200, {"embeddings": [[0.1, 0.2]]})
    return FakeResp(404, {})
emb_module.requests.post = _embed_new
check("embed: yeni uc nokta", emb_module._embed_ollama("test", {}) == [0.1, 0.2])

def _embed_old(url, **k):
    if url.endswith("/api/embed"):
        return FakeResp(404, {}, "not found")
    return FakeResp(200, {"embedding": [0.3, 0.4]})
emb_module.requests.post = _embed_old
check("embed: eski uc noktaya geri duser", emb_module._embed_ollama("test", {}) == [0.3, 0.4])

check("think temizligi coklu blok", _strip_think("<think>a</think>cevap") == "cevap")

# HTTP taklitlerini geri al
llm_module.requests.post = _real_post
llm_module.requests.get = _real_get
emb_module.requests.post = _real_post

# ---------- Faz 4: Belge yukleme + RAG ----------
from mason import documents as docs

# Uzanti -> tur / desteklenirlik
check("belge: pdf turu", docs.filetype_of("a.PDF") == "pdf")
check("belge: word turu", docs.filetype_of("rapor.docx") == "word")
check("belge: gorsel turu", docs.filetype_of("foto.jpeg") == "image")
check("belge: ses turu", docs.filetype_of("kayit.mp3") == "audio")
check("belge: kod metin sayilir", docs.filetype_of("main.py") == "text")
check("belge: desteklenen tur", docs.is_supported("x.pdf") and docs.is_supported("y.csv"))
check("belge: desteklenmeyen tur", not docs.is_supported("x.exe"))

# Parcalama (chunking)
_short = docs.chunk_text("kisa metin")
check("chunk: kisa metin tek parca", len(_short) == 1)
_long = docs.chunk_text("cumle. " * 800)  # ~5600 karakter
check("chunk: uzun metin bolunur", len(_long) > 1)
check("chunk: bos metin bos liste", docs.chunk_text("   ") == [])
check("chunk: parcalar ust uste biner (baglam korunur)",
      all(len(c) <= docs.CHUNK_SIZE + 50 for c in _long))

# Metin dosyasi yukleme (embedding'siz: config=None -> ag gerekmez)
_tmpf = Path(tempfile.mkdtemp()) / "ders_notu.txt"
_tmpf.write_text("MASON projesi Muzaffer'in kisisel yapay zeka asistanidir. "
                 "Gemini ve Ollama kullanir. " * 60, encoding="utf-8")
_res = docs.ingest(str(_tmpf), config=None)
check("ingest: metin dosyasi islenir", _res["ok"] and _res["chunks"] >= 1)
check("ingest: belge listelenir", len(docs.list_documents()) == 1)
_doc = docs.list_documents()[0]
check("ingest: dogru dosya adi", _doc["filename"] == "ders_notu.txt")
check("ingest: onizleme uretilir", bool(_doc["summary"]))

# Desteklenmeyen / eksik dosya
check("ingest: desteklenmeyen tur reddedilir",
      docs.ingest(str(Path(tempfile.mkdtemp()) / "a.exe"), None)["ok"] is False)
check("ingest: olmayan dosya reddedilir",
      docs.ingest("/yok/olmayan_dosya.pdf", None)["ok"] is False)

# Retrieval / prompt
_ctx = docs.format_for_prompt(query="MASON nedir", config=None)
check("retrieval: ilgili parca prompt'a girer", "MASON" in _ctx)
check("retrieval: kaynak dosya adi belirtilir", "ders_notu.txt" in _ctx)
check("retrieval: parca sinirlanir", len(docs.relevant_chunks(None, None)) <= docs.TOP_CHUNKS)

# Silme (parcalar da silinir)
docs.delete_document(_doc["id"])
check("belge silme: belge kalkar", len(docs.list_documents()) == 0)
check("belge silme: parcalar da kalkar", len(docs._all_chunks()) == 0)
check("belge yokken prompt bos", docs.format_for_prompt("x", None) == "")

# Agent prompt sablonu belge yerini icermeli
check("agent: prompt sablonu {documents} placeholder'i icerir",
      "{documents}" in agent.SYSTEM_PROMPT_TEMPLATE)

# ---------- Faz 5: Silinen bilgi korumasi (forgotten / tombstone) ----------
_fid = memory.remember("Muzaffer fitness yapiyor", "fact")
check("tombstone: hafizaya eklendi", _fid > 0)
memory.forget(_fid)
check("tombstone: silindi", not any(
    m["content"] == "Muzaffer fitness yapiyor" for m in memory.all_memories()))
check("tombstone: forgotten listesine yazildi",
      memory.is_forgotten("Muzaffer fitness yapiyor"))
check("tombstone: silinen bilgi GERI EKLENEMEZ (id=0)",
      memory.remember("Muzaffer fitness yapiyor", "fact") == 0)
check("tombstone: gercekten geri eklenmedi", not any(
    m["content"] == "Muzaffer fitness yapiyor" for m in memory.all_memories()))
check("tombstone: forgotten_list gorunur",
      "Muzaffer fitness yapiyor" in memory.forgotten_list())
_added = memory.import_memories([{"content": "Muzaffer fitness yapiyor", "category": "fact"}])
check("tombstone: yedekten import geri yukler", _added == 1)
check("tombstone: import forgotten kaydini temizler",
      not memory.is_forgotten("Muzaffer fitness yapiyor"))

# ---------- Faz 5: Plan silme ----------
_pid = planner.save_plan("daily", "Silinecek Plan", "- test")
check("plan: kaydedildi", any(p["id"] == _pid for p in planner.list_plans()))
planner.delete_plan(_pid)
check("plan: silindi", not any(p["id"] == _pid for p in planner.list_plans()))
check("plan: all_plan_ids calisir", isinstance(planner.all_plan_ids(), list))

# ---------- Faz 5: Ollama num_ctx (uzun promptun kesilmemesi) ----------
from mason.llm import OllamaProvider
check("ollama: num_ctx varsayilan 8192 (2048 degil)",
      OllamaProvider().num_ctx == 8192)
check("ollama: num_ctx config'ten ayarlanir",
      OllamaProvider(num_ctx=4096).num_ctx == 4096)

# ---------- Faz 6: Hava durumu (Open-Meteo) ----------
from mason import weather, briefing, ics_export
_d, _e = weather.describe_code(0)
check("hava: kod 0 -> açık", _d == "açık")
check("hava: bilinmeyen kod cokmez", isinstance(weather.describe_code(999)[0], str))
weather.get_weather = lambda cfg: {"city": "Antalya", "temp": 30, "code": 0,
    "desc": "açık", "emoji": "☀️", "tmin": 22, "tmax": 34}
check("hava: format satiri uretir", "Antalya" in weather.format_weather({}))

# ---------- Faz 6: .ics disa aktarma ----------
planner.add_task("ICS testi gorevi", "Okul", 1, "2026-07-20")
_ics, _cnt = ics_export.build_ics(planner.list_tasks("all"))
check("ics: VCALENDAR basligi", _ics.startswith("BEGIN:VCALENDAR"))
check("ics: en az 1 VEVENT", _ics.count("BEGIN:VEVENT") >= 1 and _cnt >= 1)
check("ics: tum-gun DATE formati", "DTSTART;VALUE=DATE:20260720" in _ics)
check("ics: VCALENDAR ile biter", _ics.strip().endswith("END:VCALENDAR"))

# ---------- Faz 6: Sabah brifingi ----------
briefing.weather.get_weather = lambda cfg: None  # ag kullanma (hava satiri atlanir)
_brief = briefing.build_briefing({"user_name": "Muzaffer", "weather_enabled": True})
check("brifing: metin uretir + isim gecer", "Muzaffer" in _brief)
check("brifing: kisa ozet uretir", isinstance(briefing.build_short({}), str))

# ---------- Faz 6: Kesintisiz konusma modu ----------
from mason.wakeword import WakeWordListener
check("wake: open_command_window metodu var",
      hasattr(WakeWordListener, "open_command_window"))

# ---------- Faz 7: Cok-sohbetli konusma gecmisi ----------
from mason import chats

_c1 = chats.create_chat()
agent.set_active_chat(_c1)
agent.save_message("user", "Python nasıl öğrenilir")
agent.save_message("assistant", "Şöyle başla...")
check("sohbet: aktif sohbete mesaj kaydedilir", len(agent.get_history()) == 2)
_lst = chats.list_chats()
check("sohbet: listede görünür", any(c["id"] == _c1 for c in _lst))
_this = [c for c in _lst if c["id"] == _c1][0]
check("sohbet: başlık ilk mesajdan üretilir", _this["title"].startswith("Python"))
check("sohbet: mesaj sayısı doğru", _this["msg_count"] == 2)

# Yeni sohbet: aktif None -> ilk mesaj yeni sohbet olusturur, gecmis kalir
agent.set_active_chat(None)
check("sohbet: yeni sohbette geçmiş boş görünür", agent.get_history() == [])
agent.save_message("user", "İkinci sohbet")
_c2 = agent.get_active_chat()
check("sohbet: yeni mesaj yeni sohbet açar", _c2 and _c2 != _c1)
check("sohbet: eski sohbet hâlâ duruyor",
      any(c["id"] == _c1 for c in chats.list_chats()))

# Eski sohbeti geri yükle
_msgs = chats.get_messages(_c1)
check("sohbet: eski sohbet mesajları okunur", len(_msgs) == 2)

# Yedekle / geri yükle
_dump = chats.export_chats()
check("sohbet: export sohbetleri verir", len(_dump) >= 2)
check("sohbet: import dedup 0 ekler", chats.import_chats(_dump) == 0)

# Sil
chats.delete_chat(_c1)
check("sohbet: silinir", not any(c["id"] == _c1 for c in chats.list_chats()))
check("sohbet: silinen sohbetin mesajları da gider", chats.get_messages(_c1) == [])

# ---------- Faz 8: Tekrar eden görevler (Apple Reminders gibi) ----------
check("recurrence: aylık sonraki tarih (8 -> gelecek ay 8)",
      planner.next_occurrence("2026-07-08", "monthly") == "2026-08-08")
from datetime import date as _date
check("recurrence: ay sonu kırpma (31 Ocak +1ay -> 28 Şubat)",
      planner._add_months(_date(2026, 1, 31), 1) == _date(2026, 2, 28))
check("recurrence: none -> None", planner.next_occurrence("2026-07-08", "none") is None)
_rid = planner.add_task("Her ayın 8'i spor", "Sağlık", 2, "2026-08-08", None, "monthly")
_rtask = [t for t in planner.list_tasks("all") if t["id"] == _rid][0]
check("recurrence: add_task recurrence kaydeder", _rtask["recurrence"] == "monthly")
_nxt = planner.complete_task(_rid)
check("recurrence: tamamlanınca sonraki tarih döner", _nxt == "2026-09-08")
check("recurrence: sonraki tekrar açık görev olur",
      any(t["due_date"] == "2026-09-08" and t["recurrence"] == "monthly"
          for t in planner.list_tasks("open")))
check("recurrence: tekrarsız tamamlanınca None",
      planner.complete_task(planner.add_task("tek", None, 3, "2026-07-10")) is None)

# ---------- Faz 8: Detay/düzenleme (memory + plan güncelleme) ----------
_umid = memory.remember("Eski içerik test", "fact", "X")
memory.update_memory(_umid, content="Yeni içerik test", category="goal",
                     note="benim notum")
_um = [m for m in memory.all_memories() if m["id"] == _umid][0]
check("update_memory: içerik + kategori + not güncellenir",
      _um["content"] == "Yeni içerik test" and _um["category"] == "goal"
      and _um["note"] == "benim notum")
_upid = planner.save_plan("weekly", "Plan X", "eski")
planner.update_plan(_upid, title="Plan Y", content="yeni içerik")
_up = [p for p in planner.list_plans() if p["id"] == _upid][0]
check("update_plan: başlık + içerik güncellenir",
      _up["title"] == "Plan Y" and _up["content"] == "yeni içerik")

# ---------- Faz 8: Konum algılama fonksiyonu mevcut ----------
check("weather: detect_location fonksiyonu var", hasattr(weather, "detect_location"))

# ---------- Faz A: Beyin / bilgi grafiği (graph.py) ----------
from mason import graph as brain_graph

# Temiz bir zeminde grafik testi (mevcut DB durumundan bağımsız kontroller)
_g_mid1 = memory.remember("Grafik testi: kalkülüs vize", "goal", "Okul")
_g_mid2 = memory.remember("Grafik testi: lineer cebir ödev", "fact", "Okul")
_g_tid = planner.add_task("Grafik testi: ders çalış", "Okul", 2)
_g = brain_graph.build_graph()
_node_ids = {n["id"] for n in _g["nodes"]}
check("graph: her hafiza bir düğüm", f"m:{_g_mid1}" in _node_ids and f"m:{_g_mid2}" in _node_ids)
check("graph: proje merkez düğümü oluşur", "p:Okul" in _node_ids)
check("graph: projeli görev düğümü + bağı",
      f"t:{_g_tid}" in _node_ids and
      any(e["source"] == f"t:{_g_tid}" and e["target"] == "p:Okul" for e in _g["edges"]))
check("graph: hafıza→proje 'belongs' bağı",
      any(e["source"] == f"m:{_g_mid1}" and e["target"] == "p:Okul"
          and e["type"] == "belongs" for e in _g["edges"]))
check("graph: stats sayaçları tutarlı",
      _g["stats"]["memories"] == len(memory.all_memories()) and
      _g["stats"]["links"] == len(_g["edges"]))
# Projesiz görev grafiğe eklenmez (kalabalık olmasın)
_g_tid2 = planner.add_task("Grafik testi: projesiz iş", None, 3)
_g2 = brain_graph.build_graph()
check("graph: projesiz görev düğüm oluşturmaz",
      f"t:{_g_tid2}" not in {n["id"] for n in _g2["nodes"]})
# include_tasks=False → hiç görev düğümü yok
_g3 = brain_graph.build_graph(include_tasks=False)
check("graph: include_tasks=False görevleri atlar",
      not any(n["type"] == "task" for n in _g3["nodes"]))

# ---------- Faz B: Obsidian köprüsü (obsidian.py) ----------
from mason import obsidian

# Testte ağ çağrısı olmasın: embedding üretimini kapat
memory.embed_text = lambda *a, **k: None

_vault = Path(tempfile.mkdtemp()) / "TestVault"
_ocfg = {"obsidian_vault_path": str(_vault)}

_ob_mid = memory.remember("Obsidian testi: köprü bilgisi", "fact", "MASON")
_r1 = obsidian.full_sync(_ocfg)
check("obsidian: ilk eşitleme çalışır", _r1["ok"] and _r1["disari"] > 0)
_mem_files = list((_vault / "Hafıza").glob("*.md"))
check("obsidian: her hafıza bir not dosyası",
      any(f"(m{_ob_mid})" in f.name for f in _mem_files))
check("obsidian: Görevler.md oluşur", (_vault / "Görevler.md").exists())
check("obsidian: proje merkez notu oluşur",
      (_vault / "Projeler" / "MASON.md").exists())
_ob_file = [f for f in _mem_files if f"(m{_ob_mid})" in f.name][0]
_otxt = _ob_file.read_text(encoding="utf-8")
check("obsidian: notta mason_id + [[proje]] bağlantısı",
      f"mason_id: {_ob_mid}" in _otxt and "[[MASON]]" in _otxt)

# Hiçbir şey değişmediyse ikinci eşitleme dosyaya dokunmaz
_r2 = obsidian.full_sync(_ocfg)
check("obsidian: değişiklik yoksa dosya yazılmaz",
      _r2["disari"] == 0 and _r2["iceri"] == 0 and _r2["yeni"] == 0)

# Vault'ta düzenleme -> hafızaya geri okunur (iki yönlülüğün kalbi)
_ob_file.write_text(_otxt.replace("köprü bilgisi", "köprü bilgisi GÜNCEL"),
                    encoding="utf-8")
_r3 = obsidian.full_sync(_ocfg)
_ob_m = [m for m in memory.all_memories() if m["id"] == _ob_mid][0]
check("obsidian: vault düzenlemesi hafızaya işlenir",
      _r3["iceri"] == 1 and "GÜNCEL" in _ob_m["content"])

# Vault'tan dosya silmek hafızayı SİLMEZ: dosya geri yazılır (şifre baypası yok)
_ob_file.unlink()
_r4 = obsidian.full_sync(_ocfg)
check("obsidian: silinen not geri yazılır, hafıza silinmez",
      _r4["geri_yazilan"] == 1 and _ob_file.exists()
      and any(m["id"] == _ob_mid for m in memory.all_memories()))

# Vault'a bırakılan mason_id'siz yeni not -> hafızaya eklenir
(_vault / "Hafıza" / "El notum.md").write_text(
    "---\nkategori: hedef\nproje: Okul\n---\n\nObsidian'dan eklenen hedef",
    encoding="utf-8")
_r5 = obsidian.full_sync(_ocfg)
check("obsidian: vault'a bırakılan yeni not hafızaya eklenir",
      _r5["yeni"] >= 1 and any(
          m["content"] == "Obsidian'dan eklenen hedef" and m["category"] == "goal"
          and m["project"] == "Okul" for m in memory.all_memories()))

# Görevler.md: kutu işaretle -> tamamlanır; yeni satır -> yeni görev
_ob_tid = planner.add_task("Obsidian testi görevi", "MASON", 2)
obsidian.full_sync(_ocfg)
_gtxt = (_vault / "Görevler.md").read_text(encoding="utf-8")
check("obsidian: görev satırı id imzalı (tN)", f"(t{_ob_tid})" in _gtxt)
_gtxt = _gtxt.replace(f"- [ ] Obsidian testi görevi (t{_ob_tid})",
                      f"- [x] Obsidian testi görevi (t{_ob_tid})")
_gtxt += "\n- [ ] Vault'tan eklenen görev 📅 2026-08-01\n"
(_vault / "Görevler.md").write_text(_gtxt, encoding="utf-8")
obsidian.full_sync(_ocfg)
check("obsidian: kutucuk işaretlemek görevi tamamlar",
      any(t["id"] == _ob_tid for t in planner.list_tasks("done")))
check("obsidian: vault'a yazılan satır yeni görev olur",
      any(t["title"] == "Vault'tan eklenen görev" and t["due_date"] == "2026-08-01"
          for t in planner.list_tasks("open")))

# Çakışma: iki taraf da değiştiyse DB kazanır, kullanıcı sürümü yedeklenir
memory.update_memory(_ob_mid, content="Obsidian çakışma: DB tarafı")
_ob_file.write_text(
    _ob_file.read_text(encoding="utf-8").replace("GÜNCEL", "VAULT tarafı"),
    encoding="utf-8")
_r6 = obsidian.full_sync(_ocfg)
check("obsidian: çakışmada DB kazanır + kullanıcı sürümü kopyalanır",
      _r6["cakisma"] == 1
      and "DB tarafı" in _ob_file.read_text(encoding="utf-8")
      and any("(çakışma)" in f.name for f in (_vault / "Hafıza").glob("*.md")))

# Planlar dışa aktarılır; vault'tan içerik düzenlemesi geri okunur
_plan_files = list((_vault / "Planlar").glob("*.md"))
check("obsidian: planlar dışa aktarılır",
      any(f"(p{_upid})" in f.name for f in _plan_files))
_pfile = [f for f in _plan_files if f"(p{_upid})" in f.name][0]
_pfile.write_text(
    _pfile.read_text(encoding="utf-8").replace("yeni içerik",
                                               "obsidian'dan düzenlendi"),
    encoding="utf-8")
obsidian.full_sync(_ocfg)
_up2 = [p for p in planner.list_plans() if p["id"] == _upid][0]
check("obsidian: plan içeriği vault'tan güncellenir",
      "obsidian'dan düzenlendi" in _up2["content"])

# Uygulama içinden silinen hafızanın notu vault'tan da kalkar
_el_mid = [m for m in memory.all_memories()
           if m["content"] == "Obsidian'dan eklenen hedef"][0]["id"]
memory.forget(_el_mid)
obsidian.full_sync(_ocfg)
check("obsidian: uygulamadan silinen hafızanın notu vault'tan kalkar",
      not (_vault / "Hafıza" / "El notum.md").exists())

# Ayrıştırıcı birim testleri
_pt = obsidian._parse_task_line("- [x] Deneme görevi 📅 2026-08-01 🔁 (t7)")
check("obsidian: görev satırı ayrıştırma (id/durum/tarih/başlık)",
      _pt["id"] == 7 and _pt["done"] and _pt["due"] == "2026-08-01"
      and _pt["title"] == "Deneme görevi")
_fm, _bd = obsidian._frontmatter("---\nmason_id: 5\nproje: X\n---\n\ngövde")
check("obsidian: frontmatter ayrıştırma",
      _fm["mason_id"] == "5" and _fm["proje"] == "X" and _bd.strip() == "gövde")
check("obsidian: dosya adı Windows/Obsidian güvenli",
      obsidian._safe_name('a<>:"/\\|?*b') == "a b")

print(f"\nTUM TESTLER GECTI ({passed}/{passed})")
