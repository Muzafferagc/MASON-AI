"""
briefing.py - Sabah brifingi (gunluk gundem)

Gunun ilk selami: saate gore selam + tarih + hava durumu + bugunku ve
gecikmis gorevler + (varsa) bugunku plan ozeti. run.py bunu belirlenen
saatte hem bildirim hem de (istege bagli) sesli olarak sunar.
"""
from datetime import date, datetime

from . import planner, reminders, weather

_GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
       "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _greeting(now: datetime, name: str) -> str:
    h = now.hour
    if h < 6:
        sel = "İyi geceler"
    elif h < 12:
        sel = "Günaydın"
    elif h < 18:
        sel = "İyi günler"
    else:
        sel = "İyi akşamlar"
    return f"{sel}, {name}."


def build_briefing(config: dict, include_weather: bool = True) -> str:
    """Sabah brifingi metnini uretir (sesli okunabilir, sade)."""
    now = datetime.now()
    name = config.get("user_name", "Muzaffer")
    lines = [_greeting(now, name)]
    lines.append(f"Bugün {now.day} {_AY[now.month]} {_GUN[now.weekday()]}.")

    if include_weather:
        w = weather.format_weather(config)
        if w:
            lines.append(w)

    due = reminders.due_tasks(days_ahead=1)
    if due["overdue"]:
        titles = ", ".join(t["title"] for t in due["overdue"][:5])
        lines.append(f"Gecikmiş {len(due['overdue'])} görevin var: {titles}.")
    if due["today"]:
        titles = ", ".join(t["title"] for t in due["today"][:6])
        lines.append(f"Bugün için {len(due['today'])} görev: {titles}.")
    if due["soon"]:
        titles = ", ".join(t["title"] for t in due["soon"][:4])
        lines.append(f"Yakında: {titles}.")

    open_tasks = planner.list_tasks("open")
    if not (due["overdue"] or due["today"] or due["soon"]):
        if open_tasks:
            lines.append(f"Bugün için tarihli görevin yok; toplam {len(open_tasks)} "
                         "açık görevin var. İstersen bugüne plan yapalım.")
        else:
            lines.append("Ajandan tertemiz. Bugün ne yapmak istediğini söyle, "
                         "planlayalım.")

    # Bugun kayitli bir plan varsa (ayni gun olusturulmus) kisa hatirlat
    today_iso = date.today().isoformat()
    for pl in planner.list_plans(limit=5):
        if (pl.get("created_at") or "").startswith(today_iso):
            lines.append(f"Not: bugün '{pl['title']}' planını kaydetmiştin.")
            break

    return "\n".join(lines)


def build_short(config: dict) -> str:
    """Bildirim (toast) icin kisa tek-iki satir ozet."""
    due = reminders.due_tasks(days_ahead=1)
    parts = []
    if due["overdue"]:
        parts.append(f"{len(due['overdue'])} gecikmiş")
    if due["today"]:
        parts.append(f"{len(due['today'])} bugün")
    if due["soon"]:
        parts.append(f"{len(due['soon'])} yakında")
    if not parts:
        return "Bugün tarihli görevin yok. Güzel bir gün olsun!"
    return "Görevler: " + ", ".join(parts) + "."
