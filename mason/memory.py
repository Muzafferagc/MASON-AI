"""
memory.py - Mason'un kalici hafizasi
Her hafiza tek bir bilgidir; kategorisi ve bagli oldugu proje ile
"agac dallari" gibi birbirine baglanir.

Faz 1.5: Her hafizanin bir de "embedding" vektoru vardir. Hafiza sayisi
azken hepsi LLM'e verilir; cogaldiginda soruyla ANLAMCA en ilgili olanlar
secilir (anlamsal arama / RAG). Embedding alinamazsa en yeniler kullanilir.
"""
import json

from .database import get_conn, rows_to_dicts
from .embeddings import embed_text, cosine_similarity

VALID_CATEGORIES = {"project", "goal", "preference", "fact"}


def update_memory(memory_id: int, content: str | None = None,
                  category: str | None = None, project: str | None = None,
                  note: str | None = None, config: dict | None = None) -> None:
    """Bir hafizayi duzenler (detay panelinden). content degisirse embedding
    yeniden uretilir. note = kullanicinin ekledigi serbest aciklama."""
    fields: dict = {}
    if content is not None and str(content).strip():
        fields["content"] = content.strip()
    if category is not None:
        fields["category"] = category if category in VALID_CATEGORIES else "fact"
    if project is not None:
        fields["project"] = project.strip() or None
    if note is not None:
        fields["note"] = note
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE memories SET {set_clause} WHERE id = ?",
            (*fields.values(), memory_id),
        )
    if "content" in fields and config:
        emb = embed_text(fields["content"], config)
        if emb:
            with get_conn() as conn:
                conn.execute("UPDATE memories SET embedding = ? WHERE id = ?",
                             (json.dumps(emb), memory_id))

# Bu sayiya kadar hafiza varsa arama yapmadan HEPSI prompt'a konur
SEMANTIC_SEARCH_THRESHOLD = 40
# Anlamsal arama actiginda prompt'a konacak hafiza sayisi
TOP_K = 30


def remember(content: str, category: str = "fact",
             project: str | None = None, config: dict | None = None,
             force: bool = False) -> int:
    """Yeni bir bilgiyi hafizaya kaydeder. Ayni icerik varsa tekrar eklemez.

    Kullanici bu bilgiyi daha once SILDIYSE (forgotten listesinde) ve force=False
    ise, Mason'un sohbet gecmisinden onu sessizce geri eklemesi ENGELLENIR
    (id=0 doner). Geri istenirse yedekten import edilir (o zaman forgotten
    kaydi temizlenir) ya da kullanici bilerek force ile ekler."""
    category = category if category in VALID_CATEGORIES else "fact"
    if not force and is_forgotten(content):
        return 0  # kullanicinin bilerek sildigi bilgi geri eklenmez
    embedding = embed_text(content, config) if config else None
    emb_json = json.dumps(embedding) if embedding else None
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM memories WHERE content = ?", (content,)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO memories (content, category, project, embedding) "
            "VALUES (?, ?, ?, ?)",
            (content, category, project, emb_json),
        )
        return cur.lastrowid


def _tombstone(conn, content: str | None) -> None:
    """Silinen bir bilginin icerigini 'forgotten' listesine ekler."""
    if content:
        conn.execute(
            "INSERT OR IGNORE INTO forgotten (content) VALUES (?)", (content,)
        )


def is_forgotten(content: str) -> bool:
    """Bu icerik daha once kullanici tarafindan silindi mi?"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM forgotten WHERE content = ?", (content,)
        ).fetchone()
    return row is not None


def forgotten_list(limit: int = 40) -> list[str]:
    """Silinmis (yeniden hatirlanmamasi gereken) bilgilerin icerigi."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT content FROM forgotten ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [r["content"] for r in rows]


def forget(memory_id: int) -> None:
    """Bir hafiza kaydini siler ve icerigini 'forgotten' listesine yazar ki
    Mason onu sohbet gecmisinden yeniden hatirlayip geri eklemesin."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        _tombstone(conn, row["content"] if row else None)
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))


def all_memory_ids() -> list[int]:
    """Tum hafiza id'lerini dondurur (toplu silme / sifre onayi icin)."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM memories ORDER BY id DESC").fetchall()
    return [r["id"] for r in rows]


def forget_all() -> int:
    """TUM hafizayi siler; silinen kayit sayisini dondurur. Silinen tum
    icerikler 'forgotten' listesine yazilir (geri hatirlanmasin).
    Not: Sifre korumasi agent katmaninda uygulanir; burasi ham silmedir."""
    with get_conn() as conn:
        for r in conn.execute("SELECT content FROM memories").fetchall():
            _tombstone(conn, r["content"])
        cur = conn.execute("DELETE FROM memories")
        return cur.rowcount


def export_memories() -> list[dict]:
    """Tum hafizayi yedeklenebilir (JSON'a uygun) sozluk listesi olarak verir.
    Embedding'ler yedege dahil edilmez; geri yuklemede yeniden uretilir."""
    items = []
    for m in all_memories(limit=1000000):
        items.append({
            "content": m["content"],
            "category": m.get("category", "fact"),
            "project": m.get("project"),
            "created_at": m.get("created_at"),
        })
    return items


def import_memories(items: list[dict], config: dict | None = None) -> int:
    """Yedekten hafizalari geri yukler. Ayni icerik zaten varsa atlanir.
    Yeni EKLENEN kayit sayisini dondurur."""
    existing = {m["content"] for m in all_memories(limit=1000000)}
    added = 0
    for it in items or []:
        content = (it.get("content") or "").strip()
        if not content or content in existing:
            continue
        category = it.get("category") or "fact"
        # Yedekten geri yukleme kullanicinin ACIK istegidir: bu icerik daha once
        # silinmis olsa bile 'forgotten' kaydini temizleyip force ile ekle.
        with get_conn() as conn:
            conn.execute("DELETE FROM forgotten WHERE content = ?", (content,))
        remember(content, category, it.get("project"), config, force=True)
        existing.add(content)
        added += 1
    return added


def all_memories(limit: int = 500) -> list[dict]:
    """Tum hafizalari getirir (en yeniler once)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return rows_to_dicts(rows)


def relevant_memories(query: str | None, config: dict | None) -> list[dict]:
    """Soruyla ilgili hafizalari secer.

    Strateji:
      1. Hafiza sayisi azsa -> hepsini dondur (arama gereksiz)
      2. Coksa -> sorunun embedding'i ile anlam benzerligine gore sirala
      3. Embedding alinamazsa -> en yeni hafizalari dondur (guvenli mod)
    """
    memories = all_memories()
    if len(memories) <= SEMANTIC_SEARCH_THRESHOLD:
        return memories

    query_emb = embed_text(query, config) if (query and config) else None
    if not query_emb:
        return memories[:TOP_K]  # guvenli mod: en yeniler

    scored, no_embedding = [], []
    for m in memories:
        if m.get("embedding"):
            try:
                emb = json.loads(m["embedding"])
                scored.append((cosine_similarity(query_emb, emb), m))
            except (json.JSONDecodeError, TypeError):
                no_embedding.append(m)
        else:
            no_embedding.append(m)

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [m for _, m in scored[:TOP_K]]
    # Embedding'i olmayan en yeni birkac kaydi da ekle (hicbiri kaybolmasin)
    result.extend(no_embedding[:5])
    return result


def memory_tree() -> dict:
    """Hafizalari proje bazinda gruplar - arayuzdeki agac gorunumu icin."""
    tree: dict[str, list[dict]] = {}
    for m in all_memories():
        key = m["project"] or "Genel"
        tree.setdefault(key, []).append(m)
    return tree


def format_for_prompt(query: str | None = None, config: dict | None = None) -> str:
    """Soruyla ilgili hafizalari LLM'in okuyacagi metin haline getirir."""
    memories = relevant_memories(query, config)
    if not memories:
        return "(no memories yet)"
    lines = []
    for m in reversed(memories):  # eskiden yeniye
        proj = f" [proje: {m['project']}]" if m["project"] else ""
        lines.append(f"- (#{m['id']}, {m['category']}{proj}) {m['content']}")
    return "\n".join(lines)


def backfill_embeddings(config: dict, max_items: int = 20) -> int:
    """Embedding'i olmayan eski hafizalara embedding ekler (arka plan isi)."""
    count = 0
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, content FROM memories WHERE embedding IS NULL LIMIT ?",
            (max_items,),
        ).fetchall()
    for r in rows:
        emb = embed_text(r["content"], config)
        if emb:
            with get_conn() as conn:
                conn.execute(
                    "UPDATE memories SET embedding = ? WHERE id = ?",
                    (json.dumps(emb), r["id"]),
                )
            count += 1
    return count
