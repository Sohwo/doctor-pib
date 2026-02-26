import fitz
import requests
from bs4 import BeautifulSoup
import os, json, hashlib, datetime

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_db():
    if not SUPABASE_AVAILABLE or not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

def make_id(text):
    return hashlib.md5(text[:200].encode()).hexdigest()[:12]

def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks

def load_sources():
    db = get_db()
    if not db:
        if os.path.exists("sources.json"):
            with open("sources.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    result = db.table("sources").select("*").execute()
    return result.data or []

def save_sources(sources):
    with open("sources.json", "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

def save_source_chunks(chunks):
    db = get_db()
    if not db:
        existing = load_sources()
        existing_ids = {s["id"] for s in existing}
        new = [c for c in chunks if c["id"] not in existing_ids]
        existing.extend(new)
        save_sources(existing)
        return len(new)
    existing = db.table("sources").select("id").execute()
    existing_ids = {s["id"] for s in (existing.data or [])}
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]
    if new_chunks:
        for i in range(0, len(new_chunks), 50):
            batch = new_chunks[i:i+50]
            clean = [{
                "id": c["id"],
                "source_type": c["source_type"],
                "source_name": c["source_name"],
                "source_url": c.get("source_url", ""),
                "content": c["content"],
                "chunk_index": c.get("chunk_index", 0),
                "total_chunks": c.get("total_chunks", 1),
                "added": c.get("added", datetime.datetime.now().isoformat())
            } for c in batch]
            db.table("sources").insert(clean).execute()
    return len(new_chunks)

def delete_source_by_name(name):
    db = get_db()
    if not db:
        sources = load_sources()
        filtered = [s for s in sources if s.get("source_name") != name]
        save_sources(filtered)
        return
    db.table("sources").delete().eq("source_name", name).execute()

def get_sources_summary():
    sources = load_sources()
    summary = {}
    for chunk in sources:
        name = chunk.get("source_name", "Sin nombre")
        if name not in summary:
            summary[name] = {
                "name": name,
                "type": chunk.get("source_type", ""),
                "chunks": 0,
                "added": chunk.get("added", ""),
                "url": chunk.get("source_url", "")
            }
        summary[name]["chunks"] += 1
    return list(summary.values())

def search_sources(query, sources, top_k=5):
    if not sources:
        return []
    query_words = set(query.lower().split())
    scored = []
    for chunk in sources:
        content_lower = chunk["content"].lower()
        score = sum(1 for w in query_words if w in content_lower)
        if query.lower() in content_lower:
            score += 5
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

def format_context(relevant_chunks):
    if not relevant_chunks:
        return ""
    ctx = "\n\n═══ FUENTES DE TUS LIBROS ═══\n"
    for i, chunk in enumerate(relevant_chunks, 1):
        ctx += f"\n[Fuente {i} — {chunk.get('source_name','?')}]:\n{chunk['content']}\n"
    ctx += "\n══════════════════════════════\n"
    return ctx

def ingest_pdf(file_bytes, filename):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    full_text = ""
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        if page_text.strip():
            full_text += f"\n[Página {page_num + 1}]\n{page_text}"
    doc.close()
    raw_chunks = chunk_text(full_text)
    chunks = []
    for i, chunk in enumerate(raw_chunks):
        chunks.append({
            "id": make_id(chunk),
            "source_type": "pdf",
            "source_name": filename,
            "content": chunk,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "added": datetime.datetime.now().isoformat()
        })
    return chunks

def ingest_url(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DoctorPIB/2.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside","iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l for l in text.split("\n") if len(l.strip()) > 20]
    clean_text = "\n".join(lines)
    if len(clean_text) < 100:
        raise Exception("La página no tiene texto suficiente.")
    title = soup.title.string[:80] if soup.title else url
    raw_chunks = chunk_text(clean_text)
    chunks = []
    for i, chunk in enumerate(raw_chunks):
        chunks.append({
            "id": make_id(chunk),
            "source_type": "url",
            "source_name": title,
            "source_url": url,
            "content": chunk,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "added": datetime.datetime.now().isoformat()
        })
    return chunks

def ingest_text(text, label="Texto manual"):
    if len(text.strip()) < 50:
        raise Exception("Texto muy corto (mínimo 50 caracteres).")
    raw_chunks = chunk_text(text)
    chunks = []
    for i, chunk in enumerate(raw_chunks):
        chunks.append({
            "id": make_id(chunk),
            "source_type": "text",
            "source_name": label,
            "content": chunk,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "added": datetime.datetime.now().isoformat()
        })
    return chunks

def ingest_image(file_bytes, filename, gemini_model=None):
    import base64
    # Groq no soporta imágenes directamente, guardamos referencia
    chunks = [{
        "id": make_id(filename + str(len(file_bytes))),
        "source_type": "image",
        "source_name": filename,
        "content": f"Imagen escaneada: {filename}. Contenido pendiente de extracción manual.",
        "chunk_index": 0,
        "total_chunks": 1,
        "added": datetime.datetime.now().isoformat()
    }]
    return chunks