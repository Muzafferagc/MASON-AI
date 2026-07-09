"""
graph.py - MASON'un "beyni" icin bilgi grafigi (knowledge graph) katmani.

Fikir: Hafizadaki her bilgi bir DUGUM (node), aralarindaki iliskiler bir
BAG (edge). Tıpkı Obsidian'daki grafik gorunumu gibi:
  - Projeler merkez (buyuk) dugumler,
  - Her bilgi/gorev o projeye bir dal ile baglanir,
  - ANLAMCA benzer iki bilgi birbirine ince bir iplikle baglanir
    (kelime degil, ANLAM benzerligi -> "okul projesi" ile "universite odevi").

Bu katman HICBIR API cagrisi yapmaz. Benzerlik baglari, hafizalarda ZATEN
kayitli olan embedding vektorlerinden (cosine similarity) hesaplanir. Yani
cevrimdisi, hizli ve tamamen ucretsizdir. Embedding'i olmayan hafizalar yine
grafikte gorunur; sadece "benzer" ipligi cizilmez (projeye bagli kalir).
"""
import json

from .database import get_conn, rows_to_dicts
from .embeddings import cosine_similarity

# Iki hafiza arasinda "benzer" bagi cizilmesi icin gereken en dusuk benzerlik.
# 0.72 = oldukca yakin; grafigi cop yigini yapmadan gercek akrabaliklari yakalar.
SIMILARITY_THRESHOLD = 0.72
# Her hafizadan cikacak en fazla "benzer" bag sayisi (grafik kalabalik olmasin).
MAX_SIMILAR_EDGES = 3

# Kategori -> arayuzde gosterilecek Turkce etiket
CATEGORY_LABELS = {
    "project": "Proje",
    "goal": "Hedef",
    "preference": "Tercih",
    "fact": "Bilgi",
}


def _short(text: str | None, n: int = 52) -> str:
    """Uzun icerigi dugum etiketi icin kisaltir (tam metni ayri tutariz)."""
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def build_graph(include_tasks: bool = True) -> dict:
    """Hafizadan bilgi grafigini (nodes + edges + stats) uretir.

    Donen yapi arayuzun force-directed cizimi icin hazirdir:
      nodes: [{id, type, label, full, size, ...}]
      edges: [{source, target, type, weight?}]
      stats: {memories, projects, tasks, links}
    """
    with get_conn() as conn:
        mems = rows_to_dicts(conn.execute(
            "SELECT id, content, category, project, note, embedding FROM memories"
        ).fetchall())
        tasks: list[dict] = []
        if include_tasks:
            tasks = rows_to_dicts(conn.execute(
                "SELECT id, title, project, status, priority FROM tasks"
            ).fetchall())

    nodes: list[dict] = []
    edges: list[dict] = []
    projects: dict[str, str] = {}  # proje adi -> node id

    def project_node(name: str | None) -> str | None:
        """Proje merkez dugumunu (yoksa olusturarak) dondurur."""
        name = (name or "").strip()
        if not name:
            return None
        if name not in projects:
            nid = f"p:{name}"
            projects[name] = nid
            nodes.append({
                "id": nid, "type": "project", "label": name,
                "full": name, "size": 22,
            })
        return projects[name]

    # 1) Hafiza dugumleri + (varsa) proje baglari -------------------------
    emb_by_id: dict[str, list] = {}
    for m in mems:
        nid = f"m:{m['id']}"
        cat = m["category"] if m["category"] in CATEGORY_LABELS else "fact"
        nodes.append({
            "id": nid, "type": cat, "mem_id": m["id"],
            "label": _short(m["content"]), "full": m["content"],
            "project": m.get("project"), "note": m.get("note"),
            "category": cat, "size": 12,
        })
        pnode = project_node(m.get("project"))
        if pnode:
            edges.append({"source": nid, "target": pnode, "type": "belongs"})
        if m.get("embedding"):
            try:
                emb_by_id[nid] = json.loads(m["embedding"])
            except (json.JSONDecodeError, TypeError):
                pass

    # 2) Anlamsal benzerlik baglari (embedding'i olan hafizalar arasinda) --
    ids = list(emb_by_id.keys())
    per_node: dict[str, int] = {i: 0 for i in ids}
    pairs: list[tuple[float, str, str]] = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            ia, ib = ids[a], ids[b]
            sim = cosine_similarity(emb_by_id[ia], emb_by_id[ib])
            if sim >= SIMILARITY_THRESHOLD:
                pairs.append((sim, ia, ib))
    pairs.sort(key=lambda x: x[0], reverse=True)  # en guclu baglar once
    for sim, ia, ib in pairs:
        if per_node[ia] >= MAX_SIMILAR_EDGES or per_node[ib] >= MAX_SIMILAR_EDGES:
            continue
        per_node[ia] += 1
        per_node[ib] += 1
        edges.append({"source": ia, "target": ib, "type": "similar",
                      "weight": round(float(sim), 3)})

    # 3) Gorev dugumleri (yalnizca bir projeye bagli olanlar) -------------
    task_count = 0
    for t in tasks:
        pnode = project_node(t.get("project"))
        if not pnode:
            continue  # projesiz gorevler grafigi kalabaliklastirmasin
        tid = f"t:{t['id']}"
        nodes.append({
            "id": tid, "type": "task", "task_id": t["id"],
            "label": _short(t["title"]), "full": t["title"],
            "status": t.get("status"), "size": 10,
        })
        edges.append({"source": tid, "target": pnode, "type": "task"})
        task_count += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "memories": len(mems),
            "projects": len(projects),
            "tasks": task_count,
            "links": len(edges),
        },
    }
