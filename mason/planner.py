"""
planner.py - Gorev ve plan yonetimi
Mason'un planlama motoru: gorevler onceliklendirilir, planlar kaydedilir.

Faz 8: TEKRAR EDEN GOREVLER (Apple Animsatici gibi). Bir gorevin 'recurrence'
alani none/daily/weekly/monthly/yearly olabilir. Tekrarlayan bir gorev
tamamlandiginda otomatik olarak SONRAKI tarih icin yeni bir gorev acilir.
"""
from datetime import date, timedelta

from .database import get_conn, rows_to_dicts

VALID_RECUR = {"none", "daily", "weekly", "monthly", "yearly"}


# ---------- GOREVLER ----------

def add_task(title: str, project: str | None = None, priority: int = 3,
             due_date: str | None = None, notes: str | None = None,
             recurrence: str | None = None) -> int:
    priority = min(5, max(1, int(priority or 3)))
    rec = recurrence if recurrence in VALID_RECUR else "none"
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, project, priority, due_date, notes, recurrence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, project, priority, due_date, notes, rec),
        )
        return cur.lastrowid


def update_task(task_id: int, **fields) -> None:
    """Gorevin verilen alanlarini gunceller (title, priority, due_date, status,
    notes, project, recurrence)."""
    allowed = {"title", "project", "priority", "due_date", "status", "notes",
               "recurrence"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            (*updates.values(), task_id),
        )


def _add_months(d: date, months: int) -> date:
    """Bir tarihe ay ekler; ay sonlarini kirpar (or. 31 Ocak + 1 ay -> 28/29 Subat)."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    # O ayin son gunu (bir sonraki ayin 1'inden bir gun geri)
    if m == 12:
        last = 31
    else:
        last = (date(y, m + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, last))


def next_occurrence(due_date: str | None, recurrence: str | None) -> str | None:
    """Tekrarlayan bir gorevin bir SONRAKI tarihini hesaplar (YYYY-MM-DD) veya None."""
    if not due_date or recurrence not in ("daily", "weekly", "monthly", "yearly"):
        return None
    try:
        d = date.fromisoformat(str(due_date)[:10])
    except ValueError:
        return None
    if recurrence == "daily":
        nd = d + timedelta(days=1)
    elif recurrence == "weekly":
        nd = d + timedelta(weeks=1)
    elif recurrence == "monthly":
        nd = _add_months(d, 1)
    else:  # yearly
        nd = _add_months(d, 12)
    return nd.isoformat()


def complete_task(task_id: int) -> str | None:
    """Gorevi tamamlar. Tekrarlayan bir gorevse, SONRAKI tarih icin yeni bir
    gorev acar ve o tarihi (YYYY-MM-DD) dondurur; degilse None."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        keys = row.keys()
        rec = (row["recurrence"] if "recurrence" in keys else "none") or "none"
        due = row["due_date"] if "due_date" in keys else None
        conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        nxt = next_occurrence(due, rec)
        if nxt:
            conn.execute(
                "INSERT INTO tasks (title, project, priority, due_date, notes, recurrence) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (row["title"], row["project"], row["priority"], nxt,
                 row["notes"] if "notes" in keys else None, rec),
            )
        return nxt


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
    _rec = {"daily": "her gün", "weekly": "her hafta", "monthly": "her ay",
            "yearly": "her yıl"}
    lines = []
    for t in tasks:
        due = f", son tarih: {t['due_date']}" if t.get("due_date") else ""
        proj = f" [proje: {t['project']}]" if t.get("project") else ""
        notes = f" | not: {t['notes']}" if t.get("notes") else ""
        rec = t.get("recurrence")
        recur = f" 🔁 {_rec[rec]}" if rec in _rec else ""
        lines.append(f"- (#{t['id']}, oncelik {t['priority']}{due}{recur}){proj} {t['title']}{notes}")
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


def update_plan(plan_id: int, title: str | None = None,
                period: str | None = None, content: str | None = None) -> None:
    """Bir plani duzenler (detay panelinden)."""
    fields: dict = {}
    if title is not None and str(title).strip():
        fields["title"] = title.strip()
    if period is not None and str(period).strip():
        fields["period"] = period.strip()
    if content is not None and str(content).strip():
        fields["content"] = content
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE plans SET {set_clause} WHERE id = ?",
            (*fields.values(), plan_id),
        )


def delete_plan(plan_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))


def all_plan_ids() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM plans ORDER BY id DESC").fetchall()
    return [r["id"] for r in rows]
