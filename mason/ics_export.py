"""
ics_export.py - Gorevleri .ics (iCalendar) dosyasina aktarma

.ics standart takvim dosya bicimidir; Google Takvim, Outlook, Apple Takvim
hepsi acar. Boylece MASON'daki son tarihli gorevlerini tek dosyayla
kendi takvimine aktarabilirsin. Tamamen yerel/ucretsiz, dis servis gerekmez.
"""
from datetime import date, datetime

from . import planner


def _esc(text: str) -> str:
    """ICS metin kacisi (virgul, noktali virgul, ters bolu, yeni satir)."""
    t = (text or "").replace("\\", "\\\\").replace(";", "\\;")
    t = t.replace(",", "\\,").replace("\n", "\\n")
    return t


def _fold(line: str) -> str:
    """ICS satirlari 75 oktetten uzunsa katlanir (RFC 5545)."""
    if len(line) <= 73:
        return line
    out, s = [], line
    while len(s) > 73:
        out.append(s[:73])
        s = " " + s[73:]
    out.append(s)
    return "\r\n".join(out)


def build_ics(tasks: list[dict] | None = None) -> tuple[str, int]:
    """Son tarihli gorevlerden .ics metni uretir. (ics_metni, gorev_sayisi)."""
    if tasks is None:
        tasks = planner.list_tasks("all")
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//MASON AI//Gorev Takvimi//TR", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "X-WR-CALNAME:MASON Görevler",
    ]
    count = 0
    for t in tasks:
        due = t.get("due_date")
        if not due:
            continue
        try:
            d = datetime.fromisoformat(due).date()
        except ValueError:
            continue
        dend = date.fromordinal(d.toordinal() + 1)  # tum-gun etkinlik: bitis ertesi gun
        prio = t.get("priority", 3) or 3
        status = "COMPLETED" if t.get("status") == "done" else "NEEDS-ACTION"
        summary = t.get("title", "Görev")
        if t.get("status") == "done":
            summary = "✓ " + summary
        desc_parts = []
        if t.get("project"):
            desc_parts.append(f"Proje: {t['project']}")
        desc_parts.append(f"Öncelik: P{prio}")
        if t.get("notes"):
            desc_parts.append(str(t["notes"]))
        lines += [
            "BEGIN:VEVENT",
            f"UID:mason-task-{t.get('id', count)}@mason.local",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{dend.strftime('%Y%m%d')}",
            _fold(f"SUMMARY:{_esc(summary)}"),
            _fold(f"DESCRIPTION:{_esc(' — '.join(desc_parts))}"),
            f"PRIORITY:{prio}",
            f"STATUS:{status}",
            "END:VEVENT",
        ]
        count += 1
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n", count
