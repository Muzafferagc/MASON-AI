"""
obsidian.py - Faz B: Obsidian koprusu (iki yonlu vault esitleme)

Fikir: MASON'un beyni (hafiza + gorevler + planlar) gercek bir Obsidian
vault'una MARKDOWN dosyalari olarak aynalanir. Sen Obsidian'da gezinir,
duzenlersin; MASON degisiklikleri geri okur. Vault yapisi:

    MasonVault/
      MASON.md            <- kullanim kilavuzu (otomatik)
      Hafıza/             <- her hafiza = bir not  "icerik (m12).md"
      Projeler/           <- proje merkez notlari (hafizalar [[proje]] ile baglanir)
      Görevler.md         <- tum gorevler checkbox listesi (isaretle = tamamla)
      Planlar/            <- kaydedilen planlar

KURALLAR (bilincli tasarim kararlari):
  - Kimlik dosya ADINDA degil, frontmatter'daki mason_id'dedir. Dosyayi
    Obsidian'da yeniden adlandirabilirsin; MASON id'den tanir.
  - Vault'tan dosya SILMEK hafizayi SILMEZ: sonraki esitlemede dosya geri
    yazilir. Silme yalnizca uygulama icinden yapilir (sifre korumasi baypas
    edilemesin diye).
  - Iki taraf da ayni anda degistiyse VERITABANI KAZANIR; senin surumun
    "... (çakışma).md" olarak yanina kopyalanir, hicbir sey kaybolmaz.
  - Yeni not eklemek: Hafıza/ icine mason_id'siz bir .md at -> hafizaya eklenir.
    Görevler.md'ye "- [ ] baslik" satiri ekle -> gorev olarak eklenir.

Degisiklik tespiti: her dosya icin son esitlemedeki iki ozet (hash) saklanir:
  db_hash   = veritabanindan uretilen markdown'in ozeti
  file_hash = diskteki dosyanin ozeti
Boylece "hangi taraf degisti?" sorusu API'siz, ucretsiz ve hizli cevaplanir.
"""
import hashlib
import re
import threading
import time
from pathlib import Path

from .config import BASE_DIR
from .database import get_conn, rows_to_dicts
from . import memory, planner

# Ayni anda iki esitleme calismasin (arka plan dongusu + ŞİMDİ EŞİTLE butonu)
_SYNC_LOCK = threading.Lock()
# Son esitlemenin sonucu (arayuzdeki durum satiri icin)
_LAST_RESULT: dict = {}

# Vault icindeki klasor/dosya adlari
DIR_MEMORY = "Hafıza"
DIR_PROJECTS = "Projeler"
DIR_PLANS = "Planlar"
FILE_TASKS = "Görevler.md"
FILE_HOME = "MASON.md"

# kategori <-> Turkce etiket (frontmatter'da ikisi de kabul edilir)
CAT_TR = {"fact": "bilgi", "goal": "hedef", "preference": "tercih",
          "project": "proje"}
TR_CAT = {v: k for k, v in CAT_TR.items()}

STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS obsidian_sync (
    key       TEXT PRIMARY KEY,  -- m:12 / plan:3 / proj:Ad / tasks / home
    relpath   TEXT NOT NULL,     -- vault icindeki goreli yol
    db_hash   TEXT,              -- son esitlemede DB'den uretilen metnin ozeti
    file_hash TEXT,              -- son esitlemede diskteki dosyanin ozeti
    synced_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


# ---------------------------------------------------------------- yardimcilar

def vault_path(config: dict) -> Path:
    """Vault klasorunun yolu. Ayarlarda bos ise proje yanindaki MasonVault."""
    p = (config.get("obsidian_vault_path") or "").strip()
    return Path(p) if p else (BASE_DIR / "MasonVault")


def _hash(text: str) -> str:
    return hashlib.sha1(_norm(text).encode("utf-8")).hexdigest()


def _norm(text: str) -> str:
    """Satir sonlarini normalize et (Windows \\r\\n farki hash'i bozmasin)."""
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def _safe_name(text: str, max_len: int = 48) -> str:
    """Iceriden guvenli bir dosya adi uretir (Windows + Obsidian yasakli
    karakterleri temizler)."""
    text = (text or "").strip().replace("\n", " ")
    text = re.sub(r'[<>:"/\\|?*#^\[\]]', " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] or text[:max_len]
    return text.strip(" .") or "not"


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _frontmatter(text: str) -> tuple[dict, str]:
    """Basit frontmatter ayristirici: '---' bloklari arasindaki 'anahtar: deger'
    satirlarini okur. (Harici YAML kutuphanesi gerekmesin diye.)
    Doner: (alanlar sozlugu, govde metni)"""
    text = _norm(text)
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip().lower()] = v.strip().strip('"')
    body = text[end + 4:]
    return fields, body.lstrip("\n")


def _split_sections(body: str) -> tuple[str, str]:
    """Hafiza notu govdesini (icerik, not) olarak ayirir.
    '## Not' ve '## Bağlantılar' basliklari ayirici olarak kullanilir."""
    lines = _norm(body).split("\n")
    content, note = [], []
    bucket = content
    for ln in lines:
        s = ln.strip()
        if s == "## Not":
            bucket = note
            continue
        if s == "## Bağlantılar":
            bucket = None  # otomatik uretilen kisim; geri okunmaz
            continue
        if bucket is not None:
            bucket.append(ln)
    return "\n".join(content).strip(), "\n".join(note).strip()


# ------------------------------------------------------------ markdown uretimi

def _render_memory(m: dict) -> str:
    cat = m.get("category") or "fact"
    parts = [
        "---",
        "mason: hafıza",
        f"mason_id: {m['id']}",
        f"kategori: {CAT_TR.get(cat, cat)}",
    ]
    if m.get("project"):
        parts.append(f"proje: {m['project']}")
    if m.get("created_at"):
        parts.append(f"olusturuldu: {m['created_at']}")
    parts += ["---", "", (m.get("content") or "").strip()]
    if (m.get("note") or "").strip():
        parts += ["", "## Not", "", m["note"].strip()]
    if m.get("project"):
        parts += ["", "## Bağlantılar", "", f"- Proje: [[{m['project']}]]"]
    return "\n".join(parts) + "\n"


def _render_project(name: str) -> str:
    return (f"---\nmason: proje\n---\n\n# {name}\n\n"
            "> Bu not MASON tarafından otomatik üretilir. Bu projeye bağlı\n"
            "> bilgiler `[[bağlantı]]` ile buraya işaret eder — sağdaki\n"
            "> *backlinks* panelinden ve grafik görünümünden hepsini görürsün.\n")


def _task_line(t: dict) -> str:
    box = "x" if t.get("status") == "done" else " "
    line = f"- [{box}] {t['title']}"
    if t.get("due_date"):
        line += f" 📅 {t['due_date']}"
    if (t.get("recurrence") or "none") != "none":
        line += " 🔁"
    return line + f" (t{t['id']})"


def _render_tasks(tasks: list[dict]) -> str:
    parts = [
        "---", "mason: görevler", "---", "", "# Görevler", "",
        "> Kutu işaretle → MASON'da tamamlanır. Yeni `- [ ] başlık` satırı",
        "> ekle → görev olarak kaydedilir (📅 2026-01-31 ile tarih verebilirsin).",
        "> Satır silmek görevi silmez; silme uygulama içinden yapılır.", "",
    ]
    groups: dict[str, list[dict]] = {}
    for t in tasks:
        groups.setdefault((t.get("project") or "Genel").strip() or "Genel",
                          []).append(t)
    for proj in sorted(groups, key=lambda p: (p == "Genel", p.lower())):
        parts.append(f"## {proj}")
        parts += [_task_line(t) for t in groups[proj]]
        parts.append("")
    return "\n".join(parts).rstrip("\n") + "\n"


def _render_plan(p: dict) -> str:
    return (f"---\nmason: plan\nmason_id: {p['id']}\ndonem: {p.get('period') or 'custom'}\n"
            f"baslik: {(p.get('title') or '').strip()}\n---\n\n"
            + (p.get("content") or "").strip() + "\n")


def _render_home() -> str:
    return f"""---
mason: kılavuz
---

# MASON Beyni

Bu vault, MASON'un hafızasının canlı bir aynasıdır — iki yönlü eşitlenir.

- **{DIR_MEMORY}/** → her bilgi bir not. İçeriği, `kategori`yi (bilgi / hedef /
  tercih / proje) ve `proje` alanını buradan düzenleyebilirsin; MASON geri okur.
- **{DIR_PROJECTS}/** → proje merkez notları. Bilgiler `[[proje]]` bağlantısıyla
  bağlanır; grafik görünümü MASON'daki BEYİN sekmesiyle aynı yıldız kümesini verir.
- **{FILE_TASKS}** → görev kutusunu işaretle, MASON'da tamamlanır. Yeni
  `- [ ] başlık` satırı yeni görev olur.
- **{DIR_PLANS}/** → kaydedilen planlar; içeriğini düzenlersen MASON'a yansır.

Kurallar: dosya silmek hafızayı silmez (geri yazılır — silme uygulama içinden,
şifreyle). Dosyayı yeniden adlandırabilirsin; kimlik `mason_id` alanındadır.
Yeni bilgi eklemek için {DIR_MEMORY}/ içine `mason_id`siz bir not bırak.
"""


# ------------------------------------------------------------- durum (state)

def _load_state() -> dict[str, dict]:
    with get_conn() as conn:
        conn.executescript(STATE_SCHEMA)
        rows = rows_to_dicts(conn.execute("SELECT * FROM obsidian_sync").fetchall())
    return {r["key"]: r for r in rows}


def _save_state(state: dict, key: str, relpath: str, db_hash: str,
                file_hash: str) -> None:
    state[key] = {"key": key, "relpath": relpath, "db_hash": db_hash,
                  "file_hash": file_hash}
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO obsidian_sync (key, relpath, db_hash, file_hash, synced_at) "
            "VALUES (?, ?, ?, ?, datetime('now','localtime')) "
            "ON CONFLICT(key) DO UPDATE SET relpath=excluded.relpath, "
            "db_hash=excluded.db_hash, file_hash=excluded.file_hash, "
            "synced_at=excluded.synced_at",
            (key, relpath, db_hash, file_hash))


def _drop_state(state: dict, key: str) -> None:
    state.pop(key, None)
    with get_conn() as conn:
        conn.execute("DELETE FROM obsidian_sync WHERE key = ?", (key,))


# ------------------------------------------------------------------- ICE ALMA
# (vault -> veritabani)

def _conflict_copy(vault: Path, relpath: str, stats: dict) -> None:
    """Iki taraf da degismisse kullanicinin surumunu yanina kopyala (kaybolmasin)."""
    src = vault / relpath
    text = _read(src)
    if text is None:
        return
    dst = src.with_name(src.stem + " (çakışma)" + src.suffix)
    _write(dst, text)
    stats["cakisma"] += 1


def _import_memory_file(path: Path, relpath: str, state: dict,
                        mems_by_id: dict, config: dict, stats: dict,
                        vault: Path) -> None:
    text = _read(path)
    if text is None:
        return
    fm, body = _frontmatter(text)
    content, note = _split_sections(body)
    raw_cat = (fm.get("kategori") or "").strip().lower()
    cat = TR_CAT.get(raw_cat, raw_cat) or None
    proj = (fm.get("proje") or "").strip() or None

    mid = fm.get("mason_id")
    if not (mid or "").strip().isdigit():
        # mason_id YOK -> kullanicinin vault'a biraktigi YENI bilgi
        if not content:
            return
        # Acik kullanici istegi: daha once silinmis olsa bile geri eklenir
        with get_conn() as conn:
            conn.execute("DELETE FROM forgotten WHERE content = ?", (content,))
        new_id = memory.remember(content, cat or "fact", proj, config, force=True)
        if note:
            memory.update_memory(new_id, note=note)
        # Bu dosyayi bu hafizanin dosyasi olarak sahiplen (adi korunur)
        m = {"id": new_id, "content": content, "category": cat or "fact",
             "project": proj, "note": note or None, "created_at": None}
        render = _render_memory(m)
        _write(path, render)
        _save_state(state, f"m:{new_id}", relpath, _hash(render), _hash(render))
        stats["yeni"] += 1
        return

    mid = int(mid)
    m = mems_by_id.get(mid)
    if not m:
        return  # hafiza silinmis; dosya disari-aktarim asamasinda kaldirilacak

    key = f"m:{mid}"
    st = state.get(key)
    file_hash = _hash(text)
    if st and st.get("relpath") != relpath and not (vault / st["relpath"]).exists():
        st["relpath"] = relpath  # kullanici dosyayi yeniden adlandirmis
    if st and file_hash == st.get("file_hash"):
        return  # dosya degismemis
    db_changed = (not st) or _hash(_render_memory(m)) != st.get("db_hash")
    if st and db_changed:
        # Iki taraf da degismis -> DB kazanir, kullanici surumu yedeklenir
        _conflict_copy(vault, relpath, stats)
        return
    # Yalnizca dosya degismis -> degisen alanlari DB'ye isle
    fields = {}
    if content and content != (m.get("content") or "").strip():
        fields["content"] = content
    if cat and cat in memory.VALID_CATEGORIES and cat != m.get("category"):
        fields["category"] = cat
    if proj != (m.get("project") or None):
        fields["project"] = proj or ""
    if note != (m.get("note") or "").strip():
        fields["note"] = note
    if fields:
        memory.update_memory(mid, config=config, **fields)
        stats["iceri"] += 1


_TASK_RE = re.compile(r"^- \[( |x|X)\] (.+)$")


def _parse_task_line(line: str) -> dict | None:
    m = _TASK_RE.match(line.strip())
    if not m:
        return None
    done = m.group(1).lower() == "x"
    rest = m.group(2)
    tid = None
    idm = re.search(r"\s*\(t(\d+)\)\s*$", rest)
    if idm:
        tid = int(idm.group(1))
        rest = rest[: idm.start()]
    due = None
    dm = re.search(r"\s*📅\s*(\d{4}-\d{2}-\d{2})", rest)
    if dm:
        due = dm.group(1)
        rest = rest[: dm.start()] + rest[dm.end():]
    title = rest.replace("🔁", "").strip()
    return {"id": tid, "done": done, "title": title, "due": due}


def _import_tasks_file(path: Path, state: dict, stats: dict,
                       vault: Path) -> None:
    text = _read(path)
    if text is None:
        return
    st = state.get("tasks")
    file_hash = _hash(text)
    if st and file_hash == st.get("file_hash"):
        return
    tasks = planner.list_tasks("all")
    by_id = {t["id"]: t for t in tasks}
    db_changed = (not st) or _hash(_render_tasks(tasks)) != st.get("db_hash")
    if st and db_changed:
        _conflict_copy(vault, FILE_TASKS, stats)
        return
    _, body = _frontmatter(text)
    section = None
    for line in body.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        p = _parse_task_line(line)
        if not p:
            continue
        if p["id"] and p["id"] in by_id:
            t = by_id[p["id"]]
            was_done = t.get("status") == "done"
            if p["done"] and not was_done:
                planner.complete_task(p["id"])  # tekrar edenler yeni tarih acar
                stats["iceri"] += 1
            elif not p["done"] and was_done:
                planner.update_task(p["id"], status="open")
                stats["iceri"] += 1
            changes = {}
            if p["title"] and p["title"] != t.get("title"):
                changes["title"] = p["title"]
            if p["due"] and p["due"] != (t.get("due_date") or None):
                changes["due_date"] = p["due"]
            if changes:
                planner.update_task(p["id"], **changes)
                stats["iceri"] += 1
        elif p["id"] is None and p["title"]:
            # id'siz yeni satir -> yeni gorev (bulundugu ## bolumu = proje)
            proj = None if (section or "Genel") == "Genel" else section
            planner.add_task(p["title"], proj, 3, p["due"])
            if p["done"]:
                pass  # tamamlanmis dogan gorev anlamsiz; acik olarak eklenir
            stats["yeni"] += 1


def _import_plan_file(path: Path, relpath: str, state: dict,
                      plans_by_id: dict, stats: dict, vault: Path) -> None:
    text = _read(path)
    if text is None:
        return
    fm, body = _frontmatter(text)
    pid = fm.get("mason_id")
    if not (pid or "").strip().isdigit():
        # Yeni plan dosyasi -> plan olarak kaydet
        title = (fm.get("baslik") or path.stem).strip()
        period = (fm.get("donem") or "custom").strip()
        if body.strip():
            new_id = planner.save_plan(period, title, body.strip())
            p = {"id": new_id, "period": period, "title": title,
                 "content": body.strip()}
            render = _render_plan(p)
            _write(path, render)
            _save_state(state, f"plan:{new_id}", relpath, _hash(render),
                        _hash(render))
            stats["yeni"] += 1
        return
    pid = int(pid)
    p = plans_by_id.get(pid)
    if not p:
        return
    key = f"plan:{pid}"
    st = state.get(key)
    file_hash = _hash(text)
    if st and st.get("relpath") != relpath and not (vault / st["relpath"]).exists():
        st["relpath"] = relpath
    if st and file_hash == st.get("file_hash"):
        return
    db_changed = (not st) or _hash(_render_plan(p)) != st.get("db_hash")
    if st and db_changed:
        _conflict_copy(vault, relpath, stats)
        return
    fields = {}
    if body.strip() and body.strip() != (p.get("content") or "").strip():
        fields["content"] = body.strip()
    new_title = (fm.get("baslik") or "").strip()
    if new_title and new_title != (p.get("title") or "").strip():
        fields["title"] = new_title
    if fields:
        planner.update_plan(pid, **fields)
        stats["iceri"] += 1


# --------------------------------------------------------------- DISA AKTARIM
# (veritabani -> vault)

def _export_one(vault: Path, state: dict, key: str, relpath: str,
                render: str, stats: dict) -> None:
    """Tek bir varligi vault'a yazar (gerekliyse). Kurallar:
    - state yoksa veya DB tarafi degistiyse -> yaz
    - dosya silinmisse -> GERI YAZ (vault'tan silme = silme degildir)"""
    st = state.get(key)
    target = vault / (st["relpath"] if st else relpath)
    render_hash = _hash(render)
    on_disk = _read(target)
    if (st and render_hash == st.get("db_hash") and on_disk is not None
            and _hash(on_disk) == st.get("file_hash")):
        return  # her sey guncel
    if st and on_disk is None:
        stats["geri_yazilan"] += 1
    _write(target, render)
    _save_state(state, key, str(target.relative_to(vault)).replace("\\", "/"),
                render_hash, render_hash)
    stats["disari"] += 1


def _prune(vault: Path, state: dict, prefix: str, alive_keys: set,
           stats: dict) -> None:
    """Uygulama icinden silinen varliklarin dosyalarini vault'tan kaldirir."""
    for key in [k for k in list(state) if k.startswith(prefix)]:
        if key in alive_keys:
            continue
        try:
            (vault / state[key]["relpath"]).unlink(missing_ok=True)
        except OSError:
            pass
        _drop_state(state, key)


# ------------------------------------------------------------------ ANA AKIS

def full_sync(config: dict) -> dict:
    """Tam esitleme: once vault'taki degisiklikleri ICE al, sonra veritabanini
    vault'a DISA yaz. Yalnizca degisen dosyalara dokunur (hash karsilastirmasi),
    o yuzden 60 saniyede bir calismasi bile ucuz ve API maliyeti sifirdir."""
    global _LAST_RESULT
    if not _SYNC_LOCK.acquire(blocking=False):
        return {"ok": False, "error": "Eşitleme zaten çalışıyor"}
    try:
        stats = {"ok": True, "disari": 0, "iceri": 0, "yeni": 0,
                 "geri_yazilan": 0, "cakisma": 0, "uyarilar": [],
                 "zaman": time.strftime("%H:%M:%S")}
        vault = vault_path(config)
        stats["vault"] = str(vault)
        (vault / DIR_MEMORY).mkdir(parents=True, exist_ok=True)
        (vault / DIR_PROJECTS).mkdir(exist_ok=True)
        (vault / DIR_PLANS).mkdir(exist_ok=True)

        state = _load_state()
        mems = memory.all_memories(limit=100000)
        mems_by_id = {m["id"]: m for m in mems}
        plans = planner.list_plans(limit=1000)
        plans_by_id = {p["id"]: p for p in plans}

        # ---- 1) ICE ALMA: vault'ta degisen/yeni dosyalar -> DB ----
        seen_ids: set[int] = set()
        for path in sorted((vault / DIR_MEMORY).glob("*.md")):
            rel = str(path.relative_to(vault)).replace("\\", "/")
            if " (çakışma)" in path.stem:
                continue
            try:
                fm, _b = _frontmatter(_read(path) or "")
                fid = fm.get("mason_id", "")
                if fid.strip().isdigit() and int(fid) in seen_ids:
                    stats["uyarilar"].append(f"Aynı mason_id iki dosyada: {rel}")
                    continue
                if fid.strip().isdigit():
                    seen_ids.add(int(fid))
                _import_memory_file(path, rel, state, mems_by_id, config,
                                    stats, vault)
            except Exception as e:  # tek dosya hatasi esitlemeyi durdurmasin
                stats["uyarilar"].append(f"{rel}: {e}")
        try:
            if (vault / FILE_TASKS).exists():
                _import_tasks_file(vault / FILE_TASKS, state, stats, vault)
        except Exception as e:
            stats["uyarilar"].append(f"{FILE_TASKS}: {e}")
        for path in sorted((vault / DIR_PLANS).glob("*.md")):
            rel = str(path.relative_to(vault)).replace("\\", "/")
            if " (çakışma)" in path.stem:
                continue
            try:
                _import_plan_file(path, rel, state, plans_by_id, stats, vault)
            except Exception as e:
                stats["uyarilar"].append(f"{rel}: {e}")

        # ---- 2) DISA AKTARIM: guncel DB -> vault ----
        mems = memory.all_memories(limit=100000)      # ice alinanlar dahil
        tasks = planner.list_tasks("all")
        plans = planner.list_plans(limit=1000)

        _export_one(vault, state, "home", FILE_HOME, _render_home(), stats)

        alive = set()
        for m in mems:
            key = f"m:{m['id']}"
            alive.add(key)
            rel = f"{DIR_MEMORY}/{_safe_name(m['content'])} (m{m['id']}).md"
            _export_one(vault, state, key, rel, _render_memory(m), stats)
        _prune(vault, state, "m:", alive, stats)

        projects = {(m.get("project") or "").strip() for m in mems}
        projects |= {(t.get("project") or "").strip() for t in tasks}
        projects.discard("")
        alive = set()
        for name in sorted(projects):
            key = f"proj:{name}"
            alive.add(key)
            rel = f"{DIR_PROJECTS}/{_safe_name(name)}.md"
            _export_one(vault, state, key, rel, _render_project(name), stats)
        _prune(vault, state, "proj:", alive, stats)

        _export_one(vault, state, "tasks", FILE_TASKS, _render_tasks(tasks), stats)

        alive = set()
        for p in plans:
            key = f"plan:{p['id']}"
            alive.add(key)
            rel = f"{DIR_PLANS}/{_safe_name(p.get('title') or 'Plan')} (p{p['id']}).md"
            _export_one(vault, state, key, rel, _render_plan(p), stats)
        _prune(vault, state, "plan:", alive, stats)

        _LAST_RESULT = stats
        return stats
    except Exception as e:
        _LAST_RESULT = {"ok": False, "error": str(e),
                        "zaman": time.strftime("%H:%M:%S")}
        return _LAST_RESULT
    finally:
        _SYNC_LOCK.release()


def sync_status() -> dict:
    """Arayuzdeki durum satiri icin son esitleme sonucu."""
    return dict(_LAST_RESULT) if _LAST_RESULT else {"ok": None}
