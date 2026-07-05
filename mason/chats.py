"""
chats.py - Cok-sohbetli konusma gecmisi (ChatGPT/Gemini gibi)

Her sohbet (conversation) ayri kaydedilir; mesajlar bir sohbete baglidir.
Boylece eski konusmalarina donebilir, silebilir ve yedekleyebilirsin.
Baslik ilk kullanici mesajindan otomatik uretilir.
"""
from .database import get_conn, rows_to_dicts

MAX_TITLE = 48


def _clean_title(text: str) -> str:
    t = " ".join((text or "").split())[:MAX_TITLE]
    return t or "Yeni sohbet"


def create_chat(title: str | None = None) -> int:
    """Yeni bir sohbet olusturur; id dondurur."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title) VALUES (?)", (title,)
        )
        return cur.lastrowid


def touch(chat_id: int, first_user_text: str | None = None) -> None:
    """Sohbetin 'son guncelleme' zamanini yeniler; baslik bossa ilk kullanici
    mesajindan otomatik baslik atar."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now','localtime') "
            "WHERE id = ?", (chat_id,),
        )
        if first_user_text:
            row = conn.execute(
                "SELECT title FROM conversations WHERE id = ?", (chat_id,)
            ).fetchone()
            if row is not None and not (row["title"] or "").strip():
                conn.execute(
                    "UPDATE conversations SET title = ? WHERE id = ?",
                    (_clean_title(first_user_text), chat_id),
                )


def rename_chat(chat_id: int, title: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (_clean_title(title), chat_id),
        )


def list_chats(limit: int = 200) -> list[dict]:
    """Sohbetleri (en son guncellenen once) mesaj sayisi ve son mesaj onizlemesiyle
    listeler. Bos sohbetler (hic mesaji olmayan) listelenmez."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS msg_count,
                   (SELECT content FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.id DESC LIMIT 1) AS last_message
            FROM conversations c
            ORDER BY c.updated_at DESC, c.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for r in rows_to_dicts(rows):
        if not r.get("msg_count"):
            continue  # bos sohbeti gosterme
        if not (r.get("title") or "").strip():
            r["title"] = _clean_title(r.get("last_message") or "Yeni sohbet")
        out.append(r)
    return out


def get_messages(chat_id: int) -> list[dict]:
    """Bir sohbetin tum mesajlarini (eskiden yeniye) getirir."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id ASC",
            (chat_id,),
        ).fetchall()
    return rows_to_dicts(rows)


def delete_chat(chat_id: int) -> None:
    """Bir sohbeti ve tum mesajlarini siler."""
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (chat_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (chat_id,))


def all_chat_ids() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM conversations ORDER BY id DESC"
        ).fetchall()
    return [r["id"] for r in rows]


def clear_empty_chats() -> int:
    """Hic mesaji olmayan bos sohbetleri temizler (kilit tutmasin)."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id NOT IN "
            "(SELECT DISTINCT conversation_id FROM messages "
            " WHERE conversation_id IS NOT NULL)"
        )
        return cur.rowcount


# ---------- Yedekleme ----------

def export_chats() -> list[dict]:
    """Tum sohbetleri (mesajlariyla) yedeklenebilir sozluk listesine cevirir."""
    out = []
    with get_conn() as conn:
        convs = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY id ASC"
        ).fetchall()
        for c in convs:
            msgs = conn.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE conversation_id = ? ORDER BY id ASC",
                (c["id"],),
            ).fetchall()
            if not msgs:
                continue
            out.append({
                "title": c["title"], "created_at": c["created_at"],
                "updated_at": c["updated_at"],
                "messages": [dict(m) for m in msgs],
            })
    return out


def import_chats(items: list[dict]) -> int:
    """Yedekten sohbetleri geri yukler. Yeni EKLENEN sohbet sayisini dondurur.
    (Basit strateji: her sohbet yeni kayit olarak eklenir; kopya kontrolu
    baslik+ilk mesaj+mesaj sayisi ile yapilir.)"""
    existing = set()
    for c in export_chats():
        msgs = c.get("messages") or []
        key = (c.get("title"), len(msgs),
               msgs[0]["content"] if msgs else "")
        existing.add(key)

    added = 0
    for it in items or []:
        msgs = it.get("messages") or []
        if not msgs:
            continue
        key = (it.get("title"), len(msgs), msgs[0].get("content", ""))
        if key in existing:
            continue
        cid = create_chat(it.get("title"))
        with get_conn() as conn:
            for m in msgs:
                conn.execute(
                    "INSERT INTO messages (conversation_id, role, content) "
                    "VALUES (?, ?, ?)",
                    (cid, m.get("role", "user"), m.get("content", "")),
                )
            conn.execute(
                "UPDATE conversations SET updated_at = datetime('now','localtime') "
                "WHERE id = ?", (cid,),
            )
        existing.add(key)
        added += 1
    return added
