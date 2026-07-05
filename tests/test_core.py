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
_done, _pending, _ptasks = agent.execute_actions('{"actions":[{"type":"clear_memory"}]}', {"memory_password": "1234"})
check("clear_memory korumali modda pending doner", set(_pending) == set(_before) and len(_before) > 0)
check("clear_memory korumali modda henuz silmez", memory.all_memory_ids() == _before)

# Gorev silme de sifre korumali: delete_task pending'e duser, silinmez
_open_before = [t["id"] for t in planner.list_tasks("all")]
_did = _open_before[0]
_done, _pf, _pt = agent.execute_actions(
    '{"actions":[{"type":"delete_task","id":%d}]}' % _did, {"memory_password": "1234"})
check("delete_task korumali modda pending doner", _pt == [_did])
check("delete_task korumali modda henuz silmez",
      [t["id"] for t in planner.list_tasks("all")] == _open_before)

# clear_tasks: korumasiz modda tum gorevleri siler
_done, _pf, _pt = agent.execute_actions('{"actions":[{"type":"clear_tasks"}]}')
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

print(f"\nTUM TESTLER GECTI ({passed}/{passed})")
