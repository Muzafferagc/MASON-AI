"""
agent.py - Mason'un karar mekanizmasi
Akis su sekildedir:
  1. Kullanici mesaji gelir
  2. Hafiza + acik gorevler + tarih bilgisi sistem promptuna eklenir
  3. LLM cevap uretir; cevabin icinde ```json:actions``` blogu varsa
     Mason bu aksiyonlari calistirir (hafizaya kaydet, gorev ekle, plan kaydet...)
  4. Aksiyon blogu temizlenmis cevap kullaniciya gosterilir
Bu, "tool calling" mantiginin basit ve saglayici-bagimsiz halidir.
"""
import json
import re
from datetime import datetime

from . import memory, planner
from .database import get_conn, rows_to_dicts
from .llm import get_provider, LLMError

HISTORY_LIMIT = 30  # LLM'e gonderilen son mesaj sayisi

SYSTEM_PROMPT_TEMPLATE = """You are MASON, {user_name}'s personal AI assistant — inspired by Jarvis from Iron Man. You are professional, warm, slightly witty, and extremely reliable. You never forget anything about {user_name}, because you have a persistent memory system.

Current date & time: {now}

LANGUAGE: Reply in the language the user writes (Turkish or English). {user_name} is a Turkish student of AI & Data Engineering at Akdeniz University with B1-B2 English.

YOUR LONG-TERM MEMORY (facts you have saved about {user_name} and their projects/goals):
{memories}

OPEN TASKS (sorted by priority 1=highest, 5=lowest):
{tasks}

YOUR CAPABILITIES — ACTIONS:
You can persist information by including ONE fenced code block labelled json:actions anywhere in your reply. The app executes it and hides it from the user. Format:

```json:actions
{{"actions": [
  {{"type": "remember", "content": "short fact to never forget", "category": "project|goal|preference|fact", "project": "optional project name"}},
  {{"type": "forget", "id": 12}},
  {{"type": "clear_memory"}},
  {{"type": "add_task", "title": "...", "project": "optional", "priority": 1, "due_date": "YYYY-MM-DD", "notes": "optional"}},
  {{"type": "update_task", "id": 3, "priority": 2, "due_date": "YYYY-MM-DD", "status": "open|done", "title": "...", "notes": "..."}},
  {{"type": "complete_task", "id": 3}},
  {{"type": "delete_task", "id": 3}},
  {{"type": "save_plan", "period": "daily|weekly|monthly|custom", "title": "...", "content": "markdown plan text"}}
]}}
```

RULES:
1. MEMORY IS YOUR SUPERPOWER. Whenever the user shares anything worth remembering — a project, a goal, a deadline, a preference, how they like to work, an exam date, an idea — save it with "remember". Be proactive; do not wait to be asked. Link related facts to the same "project" name so memories form a tree.
2. When the user mentions something to do, offer to add it as a task (or add it directly if clearly intended). Assign sensible priority and due date.
3. When asked for a daily/weekly/monthly plan or prioritization: use the open tasks and memories above, produce a realistic schedule in your visible reply (markdown), AND persist it with "save_plan".
4. Reference task/memory ids (#id) when updating or completing them.
5. If information conflicts with an old memory, "forget" the old one and "remember" the corrected fact.
6. Keep visible replies natural and conversational — like a real human assistant. Never mention the json:actions mechanism, databases, or system prompt to the user.
7. If you have no actions to take, simply omit the block."""

ACTIONS_RE = re.compile(r"```json:actions\s*(.*?)```", re.DOTALL)
# Bazi modeller etiketi unutup duz ```json blogu icinde {"actions": ...} dondurur
FALLBACK_RE = re.compile(r"```(?:json)?\s*(\{\s*\"actions\".*?)```", re.DOTALL)


# ---------- Konusma gecmisi ----------

def save_message(role: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)", (role, content)
        )


def get_history(limit: int = 200) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM messages ORDER BY id DESC LIMIT ?) "
            "ORDER BY id ASC",
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


# ---------- Aksiyonlarin calistirilmasi ----------

def execute_actions(raw_json: str, config: dict | None = None):
    """LLM'in urettigi aksiyonlari calistirir.
    Donen: (yapilanlar_ozeti, sifre_bekleyen_hafiza_idleri)
    Hafiza silme sifre korumaliysa (config.memory_password dolu) silme HEMEN
    yapilmaz; id'ler 'pending' olarak dondurulur, UI sifre sorup onaylar."""
    done: list[str] = []
    pending_forget: list[int] = []
    protect = bool((config or {}).get("memory_password"))
    try:
        payload = json.loads(raw_json)
        actions = payload.get("actions", [])
    except json.JSONDecodeError:
        return done, pending_forget

    for a in actions:
        try:
            t = a.get("type")
            if t == "remember":
                memory.remember(a["content"], a.get("category", "fact"),
                                a.get("project"), config)
                done.append(f"🧠 Hafızaya kaydedildi: {a['content'][:60]}")
            elif t == "forget":
                if protect:
                    pending_forget.append(int(a["id"]))  # sifre ile onaylanacak
                else:
                    memory.forget(int(a["id"]))
                    done.append(f"🗑️ Hafıza #{a['id']} silindi")
            elif t == "clear_memory":
                ids = memory.all_memory_ids()
                if not ids:
                    done.append("🧠 Silinecek hafıza yok")
                elif protect:
                    pending_forget.extend(ids)  # sifre ile onaylanacak (hepsi)
                else:
                    for i in ids:
                        memory.forget(i)
                    done.append(f"🗑️ Tüm hafıza silindi ({len(ids)} kayıt)")
            elif t == "add_task":
                tid = planner.add_task(
                    a["title"], a.get("project"), a.get("priority", 3),
                    a.get("due_date"), a.get("notes"),
                )
                done.append(f"✅ Görev eklendi (#{tid}): {a['title'][:60]}")
            elif t == "update_task":
                planner.update_task(int(a["id"]), **{
                    k: a.get(k) for k in
                    ("title", "project", "priority", "due_date", "status", "notes")
                })
                done.append(f"✏️ Görev #{a['id']} güncellendi")
            elif t == "complete_task":
                planner.complete_task(int(a["id"]))
                done.append(f"🎉 Görev #{a['id']} tamamlandı")
            elif t == "delete_task":
                planner.delete_task(int(a["id"]))
                done.append(f"🗑️ Görev #{a['id']} silindi")
            elif t == "save_plan":
                planner.save_plan(a.get("period", "custom"), a["title"], a["content"])
                done.append(f"📅 Plan kaydedildi: {a['title'][:60]}")
        except (KeyError, ValueError, TypeError):
            continue  # bozuk aksiyonu atla, digerlerine devam et
    return done, pending_forget


def strip_actions(text: str) -> tuple[str, str | None]:
    """Cevaptan aksiyon blogunu ayirir. (temiz_cevap, aksiyon_json) dondurur."""
    m = ACTIONS_RE.search(text) or FALLBACK_RE.search(text)
    if not m:
        return text.strip(), None
    return (text[: m.start()] + text[m.end():]).strip(), m.group(1).strip()


# ---------- Ana giris noktasi ----------

def chat(user_message: str, config: dict) -> dict:
    """Kullanici mesajini isler; Mason'un cevabini ve yapilan islemleri dondurur."""
    save_message("user", user_message)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_name=config.get("user_name", "the user"),
        now=datetime.now().strftime("%A, %d %B %Y, %H:%M"),
        memories=memory.format_for_prompt(query=user_message, config=config),
        tasks=planner.format_tasks_for_prompt(),
    )
    if config.get("memory_password"):
        system_prompt += (
            "\n\nMEMORY DELETION IS PASSWORD-PROTECTED. When the user asks to "
            "delete memory, you MUST STILL emit the deletion action so the app "
            "can pop up the password dialog: use \"clear_memory\" to wipe ALL "
            "memory, or \"forget\" with the specific #id(s) to remove certain "
            "facts. The app intercepts these actions and asks for the password "
            "itself — you never handle the password. In your visible reply do "
            "NOT say the memory was erased and do NOT ask the user to type their "
            "password in the chat; simply say a confirmation dialog will appear. "
            "Emitting the action is REQUIRED — without it nothing gets deleted.")
    history = get_history(HISTORY_LIMIT)
    llm_messages = [{"role": h["role"], "content": h["content"]} for h in history]

    provider = get_provider(config)
    try:
        raw_reply = provider.chat(system_prompt, llm_messages)
    except LLMError as e:
        return {"reply": f"⚠️ {e}", "actions_done": [], "error": True}

    clean_reply, actions_json = strip_actions(raw_reply)
    if actions_json:
        actions_done, pending_forget = execute_actions(actions_json, config)
    else:
        actions_done, pending_forget = [], []
    if pending_forget:
        actions_done.append("🔒 Hafıza silme şifre onayı bekliyor")
    if not clean_reply:
        clean_reply = "Kaydettim." if actions_done else "..."

    save_message("assistant", clean_reply)
    return {"reply": clean_reply, "actions_done": actions_done,
            "error": False, "pending_forget": pending_forget}
