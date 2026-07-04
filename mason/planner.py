"""
planner.py - Gorev ve plan yonetimi
Mason'un planlama motoru: gorevler onceliklendirilir, planlar kaydedilir.
"""
from .database import get_conn, rows_to_dicts


# ---------- GOREVLER ----------

def add_task(title: str, project: str | None = None, priority: int = 3,
             due_date: str | None = None, notes: str | None = None) -> int:
    priority = min(5, max(1, int(priority or 3)))
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, project, priority, due_date, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, project, priority, due_date, notes),
        )
        return cur.lastrowid


def update_task(task_id: int, **fields) -> None:
    """Gorevin verilen alanlarini gunceller (title, priority, due_date, status, notes, project)."""
    allowed = {"title", "project", "priority", "due_date", "status", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            (*updates.values(), task_id),
        )


def complete_task(task_id: int) -> None:
    update_task(task_id, status="done")


def delete_task(task_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def list_tasks(status: str = "open") -> list[dict]:
    """Gorevleri once oncelik, sonra tarih sirasina gore getirir."""
    with get_conn() as conn:
        if status == "all":
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY status, priority, due_date IS NULL, due_date"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? "
                "ORDER BY priority, due_date IS NULL, due_date",
                (status,),
            ).fetchall()
    return rows_to_dicts(rows)


def format_tasks_for_prompt() -> str:
    """Acik gorevleri LLM'in okuyacagi metin haline getirir."""
    tasks = list_tasks("open")
    if not tasks:
        return "(no open tasks)"
    lines = []
    for t in tasks:
        due = f", son tarih: {t['due_date']}" if t["due_date"] else ""
        proj = f" [proje: {t['project']}]" if t["project"] else ""
        notes = f" | not: {t['notes']}" if t["notes"] else ""
        lines.append(f"- (#{t['id']}, oncelik {t['priority']}{due}){proj} {t['title']}{notes}")
    return "\n".join(lines)


# ---------- PLANLAR ----------

def save_plan(period: str, title: str, content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO plans (period, title, content) VALUES (?, ?, ?)",
            (period, title, content),
        )
        return cur.lastrowid


def list_plans(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM plans ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return rows_to_dicts(rows)
