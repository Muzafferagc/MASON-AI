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
    note       TEXT,                        -- kullanicinin ekledigi serbest not/aciklama
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
    recurrence TEXT DEFAULT 'none',         -- none/daily/weekly/monthly/yearly (Apple tarzi yineleme)
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Sohbetler: her sohbet ayri kaydedilir (ChatGPT/Gemini gibi gecmis)
CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT,                        -- ilk mesajdan otomatik baslik
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Konusma gecmisi: chat kalicidir (her mesaj bir sohbete baglidir)
-- NOT: messages icin index BURADA OLUSTURULMAZ. Cunku eski veritabanlarinda
-- 'messages' tablosu ZATEN VAR ama conversation_id sutunu YOK; bu index'i
-- executescript icinde olusturmaya calismak (migrasyon sutunu eklemeden ONCE
-- calistigi icin) "no such column: conversation_id" hatasi verir. Index,
-- sutun kesin var oldugu icin _migrate() sonunda olusturulur.
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,                -- bagli oldugu sohbet
    role            TEXT NOT NULL,          -- user / assistant
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Kaydedilen planlar (gunluk/haftalik/aylik)
CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    period     TEXT NOT NULL,               -- daily / weekly / monthly / custom
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,               -- markdown plan metni
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Belgeler: kullanicinin yukledigi dosyalar (PDF, Word, gorsel, ses...)
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,              -- orijinal dosya adi
    filetype    TEXT NOT NULL DEFAULT 'other', -- pdf/word/excel/image/audio/text
    stored_path TEXT,                       -- uygulamanin sakladigi kopyanin yolu
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    char_count  INTEGER NOT NULL DEFAULT 0, -- cikartilan metnin uzunlugu
    chunk_count INTEGER NOT NULL DEFAULT 0, -- kac parcaya bolundu
    summary     TEXT,                       -- kisa onizleme (ilk birkac cumle)
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Belge parcalari: RAG icin embedding'li metin parcalari (agacin yapraklari)
CREATE TABLE IF NOT EXISTS doc_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      INTEGER NOT NULL,           -- bagli oldugu belge
    chunk_index INTEGER NOT NULL DEFAULT 0, -- belgedeki sirasi
    content     TEXT NOT NULL,              -- parcanin metni
    embedding   TEXT,                       -- anlam vektoru (JSON listesi)
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc ON doc_chunks(doc_id);

-- Silinen bilgiler (mezar tasi): kullanici bir hafizayi silince icerigi burada
-- tutulur ki Mason onu sohbet gecmisinden yeniden hatirlayip geri EKLEMESIN.
-- Kullanici yedekten geri yuklerse (import) ilgili kayit buradan cikarilir.
CREATE TABLE IF NOT EXISTS forgotten (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    content    TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def get_conn() -> sqlite3.Connection:
    """Veritabani baglantisi acar (tablolar yoksa olusturur).

    ONEMLI: MASON'da ayni anda BIRDEN COK thread veritabanina erisir
    (sohbet + hatirlatici dongusu + brifing dongusu + embedding arka plani +
    sesli komut). Varsayilan SQLite bu durumda kolayca 'database is locked'
    hatasi verir -> sesli komut takilir/coker. Bunu onlemek icin:
      - WAL modu: okuyucular yazana engel olmaz (cok daha az kilit)
      - busy_timeout: kilit varsa hemen hata vermek yerine 8 sn bekle"""
    conn = sqlite3.connect(DB_FILE, timeout=8.0)
    conn.row_factory = sqlite3.Row  # sonuclara sozluk gibi erisim
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=8000")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        pass
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Eski veritabanlarina yeni kolonlari ekler (veri kaybetmeden)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(memories)")]
    if "embedding" not in cols:
        # Faz 1.5: hafizanin anlam vektoru (JSON listesi olarak saklanir)
        conn.execute("ALTER TABLE memories ADD COLUMN embedding TEXT")

    # Faz 8: gorevlere tekrar (recurrence) alani (Apple anismatici gibi yineleme)
    tcols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)")]
    if "recurrence" not in tcols:
        conn.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'none'")
        conn.commit()

    # Faz 8: hafizaya kullanicinin duzenleyebilecegi 'not' alani
    memcols = [r[1] for r in conn.execute("PRAGMA table_info(memories)")]
    if "note" not in memcols:
        conn.execute("ALTER TABLE memories ADD COLUMN note TEXT")
        conn.commit()

    # Faz 7: mesajlari sohbetlere bagla (cok-sohbetli gecmis)
    mcols = [r[1] for r in conn.execute("PRAGMA table_info(messages)")]
    if "conversation_id" not in mcols:
        conn.execute("ALTER TABLE messages ADD COLUMN conversation_id INTEGER")
        # Sahipsiz eski mesajlar varsa hepsini tek bir "Onceki sohbet"e tasi
        orphan = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id IS NULL"
        ).fetchone()[0]
        if orphan:
            cur = conn.execute(
                "INSERT INTO conversations (title) VALUES ('Önceki sohbet')"
            )
            conn.execute(
                "UPDATE messages SET conversation_id = ? "
                "WHERE conversation_id IS NULL",
                (cur.lastrowid,),
            )
        conn.commit()  # DDL + tasima kesin kaydedilsin (Python surumu ne olursa olsun)

    # Index'i SUTUN KESIN VAR OLDUKTAN SONRA olustur (eski DB'lerde executescript
    # icinde olusturmaya calismak cokerdi). IF NOT EXISTS oldugu icin guvenli.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)"
    )
    conn.commit()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]
