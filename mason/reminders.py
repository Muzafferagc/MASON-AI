"""
reminders.py - Yaklasan ve geciken gorevler icin hatirlatici mantigi.

Bu dosya SADECE "hangi gorevler hatirlatilmali" kararini verir (saf, test
edilebilir mantik). Windows bildirimi / arayuz uyarisi run.py tarafindan
gosterilir.
"""
from datetime import date, datetime

from . import planner


def _today() -> str:
    return date.today().isoformat()


def due_tasks(days_ahead: int = 1) -> dict:
    """Acik gorevleri hatirlatma durumuna gore ayirir.

    Donen sozluk:
      overdue -> son tarihi gecmis gorevler
      today   -> son tarihi bugun olan gorevler
      soon    -> onumuzdeki `days_ahead` gun icinde son tarihli gorevler
    """
    today = _today()
    overdue: list[dict] = []
    today_list: list[dict] = []
    soon: list[dict] = []
    for t in planner.list_tasks("open"):
        d = t.get("due_date")
        if not d:
            continue
        if d < today:
            overdue.append(t)
        elif d == today:
            today_list.append(t)
        else:
            try:
                diff = (datetime.fromisoformat(d).date() - date.today()).days
            except ValueError:
                continue
            if 0 < diff <= days_ahead:
                soon.append(t)
    return {"overdue": overdue, "today": today_list, "soon": soon}


def any_due(days_ahead: int = 1) -> bool:
    """Hatirlatilacak (gecikmis/bugun/yakinda) gorev var mi?"""
    d = due_tasks(days_ahead)
    return bool(d["overdue"] or d["today"] or d["soon"])


def format_reminder(days_ahead: int = 1) -> str | None:
    """Kisa hatirlatma metni uretir; hatirlatilacak sey yoksa None dondurur."""
    d = due_tasks(days_ahead)
    if not (d["overdue"] or d["today"] or d["soon"]):
        return None
    parts: list[str] = []
    if d["overdue"]:
        titles = ", ".join(t["title"] for t in d["overdue"][:3])
        parts.append(f"⚠️ Gecikmiş {len(d['overdue'])} görev: {titles}")
    if d["today"]:
        titles = ", ".join(t["title"] for t in d["today"][:3])
        parts.append(f"📌 Bugün: {titles}")
    if d["soon"]:
        titles = ", ".join(t["title"] for t in d["soon"][:3])
        parts.append(f"🔜 Yakında: {titles}")
    return "  |  ".join(parts)
