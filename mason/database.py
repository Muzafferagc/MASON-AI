"""
database.py - SQLite veritabani katmani
Mason'un kalici hafizasi burada yasar. Uygulama kapansa da hicbir sey silinmez.
"""
import sqlite3
from .config import DB_FILE

SCHEMA = """
-- Hafiza: Mason'un senin hakkinda ogrendigi her sey (agacin dallari)
CREATE TABLE IF NOT EXISTS memories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    content    TEXT NOT NULL,               -- hatirlanacak bilgi
    category   TEXT NOT NULL DEFAULT 'fact',-- project / goal / preference / fact
    project    TEXT,                        -- bagli oldugu proje (dal)
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Gorevler: planlama motorunun temeli
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    project    TEXT,
    priority   INTEGER NOT NULL DEFAULT 3,  -- 1 = en onemli, 5 = en dusuk
    due_date   TEXT,                        -- YYYY-MM-DD
    status     TEXT NOT NULL DEFAULT 'open',-- open / done
    notes      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Konusma gecmisi: chat kalicidir
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role       TEXT NOT NULL,               -- user / assistant
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Kaydedilen planlar (gunluk/haftalik/aylik)
CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    period     TEXT NOT NULL,               -- daily / weekly / monthly / custom
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,               -- markdown plan metni
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def get_conn() -> sqlite3.Connection:
    """Veritabani baglantisi acar (tablolar yoksa olusturur)."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # sonuclara sozluk gibi erisim
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Eski veritabanlarina yeni kolonlari ekler (veri kaybetmeden)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(memories)")]
    if "embedding" not in cols:
        # Faz 1.5: hafizanin anlam vektoru (JSON listesi olarak saklanir)
        conn.execute("ALTER TABLE memories ADD COLUMN embedding TEXT")


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]
