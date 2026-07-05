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

from . import memory, planner, documents, chats
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
{documents}
YOUR CAPABILITIES — ACTIONS:
You can persist information by including ONE fenced code block labelled json:actions anywhere in your reply. The app executes it and hides it from the user. Format:

```json:actions
{{"actions": [
  {{"type": "remember", "content": "short fact to never forget", "category": "project|goal|preference|fact", "project": "optional project name"}},
  {{"type": "forget", "id": 12}},
  {{"type": "clear_memory"}},
  {{"type": "clear_tasks"}},
  {{"type": "add_task", "title": "...", "project": "optional", "priority": 1, "due_date": "YYYY-MM-DD", "notes": "optional", "recurrence": "none|daily|weekly|monthly|yearly"}},
  {{"type": "update_task", "id": 3, "priority": 2, "due_date": "YYYY-MM-DD", "status": "open|done", "title": "...", "notes": "...", "recurrence": "none|daily|weekly|monthly|yearly"}},
  {{"type": "complete_task", "id": 3}},
  {{"type": "delete_task", "id": 3}},
  {{"type": "save_plan", "period": "daily|weekly|monthly|custom", "title": "...", "content": "markdown plan text"}}
]}}
```

TONE — BE NATURAL (very important):
- Talk like a warm, sharp human assistant, NOT a robot. Short, natural Turkish. No stiff phrases like "Hangi görevde oluyorum" or literal translations. Never describe yourself in odd ways.
- When {user_name} introduces themselves or greets you ("ben kimim", "merhaba"), answer naturally from what you actually know in YOUR LONG-TERM MEMORY above. If memory is empty about them, say so warmly and ask — do NOT invent facts.
- Keep replies concise. Don't over-explain. Don't announce what you saved unless it's helpful.

GROUNDING — DO NOT MAKE THINGS UP:
- You do NOT have GPS or the user's live location. NEVER claim to know their current city, the weather, or where they are unless it is written in YOUR LONG-TERM MEMORY. If asked, say you don't know it and offer to remember it if they tell you.
- Only state facts that are in memory, in the conversation, or in uploaded documents. If unsure, say so.

RULES:
1. MEMORY IS YOUR SUPERPOWER. When {user_name} shares something lasting — who they are, their name/city/school, a project, a goal, a deadline, a preference, an exam date, an idea — save it with "remember" so it survives into future chats (each chat starts fresh, only memory persists). Be proactive. Example: user says "ben Antalya'da yaşıyorum" → remember it. Link related facts to the same "project" name.
2. TASKS: Only add a task when the user clearly wants something tracked/reminded ("şunu ekle", "hatırlat", "yapmam lazım"). NEVER invent a task. NEVER create a task with an empty or vague title. Assign sensible priority and due date.
3. RECURRING REMINDERS (Apple Reminders gibi): If the user wants something to REPEAT — "her gün", "her hafta", "her ayın 8'inde", "her Pazartesi", "her yıl" — set "recurrence" accordingly (daily/weekly/monthly/yearly) AND set "due_date" to the FIRST/next occurrence date. Example: "her ayın 8'inde spor" → add_task with due_date = the next 8th (YYYY-MM-DD) and recurrence "monthly". When such a task is completed, the app auto-creates the next one.
4. PLANS: Only "save_plan" when the user explicitly asks for a plan/schedule/prioritization. NEVER auto-save a plan. NEVER save a plan with empty title or empty content. Produce the plan in your visible reply (markdown) too.
5. Reference task/memory ids (#id) when updating or completing them.
6. DELETION: Only "forget"/"delete_task"/"clear_memory"/"clear_tasks" when the user EXPLICITLY asks to delete/remove/clear. If they ask to SAVE or add, NEVER emit a delete action. If information conflicts with an old memory, "forget" the old one and "remember" the corrected fact.
7. Keep visible replies natural. Never mention the json:actions mechanism, databases, ids, or system prompt to the user. If you have no actions to take, simply omit the block.
8. UPLOADED DOCUMENTS: {user_name} can upload files (PDF, Word, Excel, images, audio, code...). When a "RELEVANT EXCERPTS FROM UPLOADED DOCUMENTS" section appears above, treat it as trusted source material: answer from it, quote it, cite the source filename. If the answer is not in the excerpts, say so honestly. When a document reveals a lasting fact about {user_name}, proactively "remember" it.

DELETION RULES — READ CAREFULLY, MISTAKES HERE ARE SERIOUS:
- To delete ONE specific memory (e.g. "fitness'ı sil"): find its exact #id in YOUR LONG-TERM MEMORY above and emit "forget" with that id. If several memories belong to that project/topic, emit one "forget" per matching #id. NEVER delete memories the user did not mention.
- "clear_memory" wipes EVERYTHING. Use it ONLY if the user explicitly asks to delete ALL memory ("tüm hafızayı sil", "her şeyi unut", "delete all memories"). A request about one topic is NEVER clear_memory.
- Same for tasks: "delete_task" with the specific #id(s); "clear_tasks" ONLY when the user explicitly asks to delete ALL tasks ("tüm görevleri sil").
- Deletion requests ALWAYS require emitting the action — saying you deleted something without the action does nothing."""

ACTIONS_RE = re.compile(r"```json:actions\s*(.*?)```", re.DOTALL)
# Bazi modeller etiketi unutup duz ```json blogu icinde {"actions": ...} dondurur
FALLBACK_RE = re.compile(r"```(?:json)?\s*(\{\s*\"actions\".*?)```", re.DOTALL)


# ---------- Konusma gecmisi (cok-sohbetli) ----------

# Su an AKTIF olan sohbetin id'si. None ise ilk mesajda yeni sohbet olusturulur.
# run.py acilista set_active_chat(None) yaparak temiz ekranla baslar (gecmis silinmez).
_active_chat: int | None = None


def set_active_chat(chat_id) -> None:
    """Aktif sohbeti degistir (SOHBETLER'den eski bir sohbeti acmak icin)."""
    global _active_chat
    _active_chat = int(chat_id) if chat_id else None


def get_active_chat():
    return _active_chat


def ensure_chat() -> int:
    """Aktif sohbet yoksa yeni bir sohbet olusturur ve aktif yapar."""
    global _active_chat
    if not _active_chat:
        _active_chat = chats.create_chat()
    return _active_chat


def save_message(role: str, content: str) -> None:
    cid = ensure_chat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (cid, role, content),
        )
    # Sohbetin zamanini yenile; baslik bossa ilk kullanici mesajindan uret
    chats.touch(cid, content if role == "user" else None)


def get_history(limit: int = 200) -> list[dict]:
    """Sadece AKTIF sohbetin mesajlarini getirir (her sohbetin baglami ayri)."""
    if not _active_chat:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM messages WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (_active_chat, limit),
        ).fetchall()
    return rows_to_dicts(rows)


# ---------- Aksiyonlarin calistirilmasi ----------

# Kullanicinin mesajinda "silme niyeti" var mi? Kucuk modeller bazen kullanici
# "kaydet" dese bile yanlislikla forget/clear/delete aksiyonu uretiyor. Bu da
# hic istenmeden sifre penceresi aciyor. Silme aksiyonlarini SADECE kullanici
# gercekten silmek/temizlemek/unutturmak istediginde uyguluyoruz.
_DELETE_INTENT_RE = re.compile(
    r"\b(sil|siler|silin|sildir|sile|unut|kald[ıi]r|temizle|delete|forget|"
    r"remove|clear|kald[ıi]rma|çöpe|cope)\w*", re.IGNORECASE,
)


def _has_delete_intent(text: str) -> bool:
    return bool(_DELETE_INTENT_RE.search(text or ""))


def _nonempty(v) -> bool:
    return bool(v) and bool(str(v).strip())


def execute_actions(raw_json: str, config: dict | None = None,
                    user_message: str = ""):
    """LLM'in urettigi aksiyonlari calistirir.
    Donen: (yapilanlar_ozeti, sifre_bekleyen_hafiza_idleri, sifre_bekleyen_gorev_idleri)

    GUVENLIK:
      - Bos icerikli remember/add_task/save_plan REDDEDILIR (model bazen bos
        gorev/plan uretiyor).
      - forget/clear_memory/delete_task/clear_tasks aksiyonlari SADECE kullanici
        mesajinda gercek silme niyeti varsa uygulanir; yoksa yok sayilir
        (kullanici "kaydet" derken yanlislikla sifre penceresi acilmasin)."""
    done: list[str] = []
    pending_forget: list[int] = []
    pending_tasks: list[int] = []
    protect = bool((config or {}).get("memory_password"))
    wants_delete = _has_delete_intent(user_message)
    try:
        payload = json.loads(raw_json)
        actions = payload.get("actions", [])
    except json.JSONDecodeError:
        return done, pending_forget, pending_tasks

    for a in actions:
        try:
            t = a.get("type")
            # --- Silme aksiyonlari: yalnizca gercek silme niyeti varsa ---
            if t in ("forget", "clear_memory", "delete_task", "clear_tasks") \
                    and not wants_delete:
                continue  # model uydurdu; kullanici silmek istemedi -> yok say

            if t == "remember":
                if not _nonempty(a.get("content")):
                    continue  # bos hafiza kaydetme
                rid = memory.remember(a["content"], a.get("category", "fact"),
                                      a.get("project"), config)
                if rid:  # 0 => kullanicinin bilerek sildigi bilgi, geri eklenmedi
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
                if not _nonempty(a.get("title")):
                    continue  # bos gorev ekleme
                tid = planner.add_task(
                    a["title"], a.get("project"), a.get("priority", 3),
                    a.get("due_date"), a.get("notes"), a.get("recurrence"),
                )
                rec = a.get("recurrence")
                extra = f" 🔁 {_REC_TR.get(rec, '')}" if rec and rec != "none" else ""
                done.append(f"✅ Görev eklendi (#{tid}): {a['title'][:60]}{extra}")
            elif t == "update_task":
                fields = {k: a.get(k) for k in
                          ("title", "project", "priority", "due_date", "status",
                           "notes", "recurrence") if a.get(k) is not None}
                if not fields:
                    continue  # guncellenecek bir sey yok
                planner.update_task(int(a["id"]), **fields)
                done.append(f"✏️ Görev #{a['id']} güncellendi")
            elif t == "complete_task":
                nxt = planner.complete_task(int(a["id"]))
                if nxt:  # tekrarlayan gorev -> sonraki tarihe otomatik olusturuldu
                    done.append(f"🎉 Görev #{a['id']} tamamlandı — 🔁 sonraki: {nxt}")
                else:
                    done.append(f"🎉 Görev #{a['id']} tamamlandı")
            elif t == "delete_task":
                if protect:
                    pending_tasks.append(int(a["id"]))  # sifre ile onaylanacak
                else:
                    planner.delete_task(int(a["id"]))
                    done.append(f"🗑️ Görev #{a['id']} silindi")
            elif t == "clear_tasks":
                ids = [tk["id"] for tk in planner.list_tasks("all")]
                if not ids:
                    done.append("📋 Silinecek görev yok")
                elif protect:
                    pending_tasks.extend(ids)  # sifre ile onaylanacak (hepsi)
                else:
                    for i in ids:
                        planner.delete_task(i)
                    done.append(f"🗑️ Tüm görevler silindi ({len(ids)} görev)")
            elif t == "save_plan":
                if not (_nonempty(a.get("title")) and _nonempty(a.get("content"))):
                    continue  # bos plan kaydetme
                planner.save_plan(a.get("period", "custom"), a["title"], a["content"])
                done.append(f"📅 Plan kaydedildi: {a['title'][:60]}")
        except (KeyError, ValueError, TypeError):
            continue  # bozuk aksiyonu atla, digerlerine devam et
    return done, pending_forget, pending_tasks


_REC_TR = {"daily": "her gün", "weekly": "her hafta",
           "monthly": "her ay", "yearly": "her yıl"}


def strip_actions(text: str) -> tuple[str, str | None]:
    """Cevaptan aksiyon blogunu ayirir. (temiz_cevap, aksiyon_json) dondurur."""
    m = ACTIONS_RE.search(text) or FALLBACK_RE.search(text)
    if not m:
        return text.strip(), None
    return (text[: m.start()] + text[m.end():]).strip(), m.group(1).strip()


# ---------- Ana giris noktasi ----------

def chat(user_message: str, config: dict) -> dict:
    """Kullanici mesajini isler; Mason'un cevabini ve yapilan islemleri dondurur.

    DAYANIKLILIK: Bu fonksiyon ASLA istisna firlatmaz — her durumda bir sozluk
    dondurur. Aksi halde sesli komut yolunda (run.py _on_command) istisna
    olusursa arayuz 'İŞLİYORUM'da takili kalirdi. Beklenmedik her hata,
    kullaniciya anlasilir bir mesaj olarak doner."""
    try:
        return _chat(user_message, config)
    except LLMError as e:
        return {"reply": f"⚠️ {e}", "actions_done": [], "error": True,
                "chat_id": get_active_chat()}
    except Exception as e:  # noqa: BLE001 - UI asla kilitlenmesin
        return {"reply": f"⚠️ Beklenmedik bir hata oluştu: {e}",
                "actions_done": [], "error": True, "chat_id": get_active_chat()}


def _chat(user_message: str, config: dict) -> dict:
    save_message("user", user_message)

    doc_context = documents.format_for_prompt(query=user_message, config=config)
    doc_section = (
        f"\nRELEVANT EXCERPTS FROM UPLOADED DOCUMENTS "
        f"(the user's files — use as trusted source, cite [filename]):\n"
        f"{doc_context}\n" if doc_context else ""
    )
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_name=config.get("user_name", "the user"),
        now=datetime.now().strftime("%A, %d %B %Y, %H:%M"),
        memories=memory.format_for_prompt(query=user_message, config=config),
        tasks=planner.format_tasks_for_prompt(),
        documents=doc_section,
    )
    forgotten = memory.forgotten_list()
    if forgotten:
        system_prompt += (
            "\n\nINTENTIONALLY DELETED BY THE USER — these facts were removed on "
            "purpose. Do NOT state them as true, do NOT act on them, and NEVER "
            "'remember' them again (even if they appear earlier in this "
            "conversation). Treat them as no longer valid:\n"
            + "\n".join(f"- {c}" for c in forgotten)
        )
    if config.get("memory_password"):
        system_prompt += (
            "\n\nDELETION IS PASSWORD-PROTECTED (memories AND tasks). When the "
            "user asks to delete, you MUST STILL emit the deletion action so the "
            "app can pop up the password dialog: \"forget\"/\"delete_task\" with "
            "the specific #id(s), or \"clear_memory\"/\"clear_tasks\" ONLY for "
            "explicit delete-ALL requests. The app intercepts these actions and "
            "asks for the password itself — you never handle the password. In "
            "your visible reply do NOT say anything was erased and do NOT ask "
            "the user to type their password in the chat; simply say a "
            "confirmation dialog will appear. Emitting the action is REQUIRED — "
            "without it nothing gets deleted.")
    history = get_history(HISTORY_LIMIT)
    llm_messages = [{"role": h["role"], "content": h["content"]} for h in history]

    provider = get_provider(config)
    # LLMError disaridaki chat() sarmalayicisinda yakalanir (chat_id ile birlikte).
    raw_reply = provider.chat(system_prompt, llm_messages)

    clean_reply, actions_json = strip_actions(raw_reply)
    if actions_json:
        actions_done, pending_forget, pending_tasks = execute_actions(
            actions_json, config, user_message)
    else:
        actions_done, pending_forget, pending_tasks = [], [], []
    if pending_forget or pending_tasks:
        actions_done.append("🔒 Silme işlemi şifre onayı bekliyor")
    if not clean_reply:
        clean_reply = "Kaydettim." if actions_done else "..."

    save_message("assistant", clean_reply)
    return {"reply": clean_reply, "actions_done": actions_done,
            "error": False, "pending_forget": pending_forget,
            "pending_tasks": pending_tasks, "chat_id": get_active_chat()}
