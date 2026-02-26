"""
╔══════════════════════════════════════╗
║         DOCTOR PIB v2.0              ║
║   Con RAG, PDFs, URLs, imágenes      ║
║   Ejecutar: python app.py            ║
╚══════════════════════════════════════╝
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from groq import Groq
import json, os, datetime
from sources import (
    load_sources, save_sources,
    ingest_pdf, ingest_url, ingest_text, ingest_image,
    search_sources, format_context
)
from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────
#  🔑 PON TU API KEY DE GROQ AQUÍ
# ─────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
# ─────────────────────────────────────

app = Flask(__name__, static_folder="static")
CORS(app)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

HISTORY_FILE = "conversations.json"


# ══════════════════════════════════════
#  PERSONALIDAD DEL DOCTOR PIB
# ══════════════════════════════════════
def build_system_prompt(mode, context=""):
    mode_instructions = {
        "explicacion": "Explica el concepto con claridad total. Estructura: Definición rápida → Mecanismo paso a paso → Fórmula si aplica → Ejemplo real que cualquiera entienda.",
        "socratico": "NO des la respuesta directa jamás. Haz UNA pregunta a la vez que guíe al estudiante. Celebra cada avance. Si se equivocan, di 'casi, casi...' y redirige con otra pregunta.",
        "simulador": "El estudiante da números. Tú calculas paso a paso con fórmulas explícitas. Muestra CADA sustitución. Interpreta el resultado con emoción genuina.",
        "debate": "Presenta al menos 2 escuelas económicas sobre el tema. Sé el árbitro imparcial. Muestra dónde se pelean y dónde se abrazan los economistas.",
        "quiz": "Genera una pregunta de opción múltiple (A/B/C/D). Tras la respuesta, explica con detalle por qué cada opción era correcta o trampa.",
        "detector": "Analiza el razonamiento del estudiante línea por línea. Marca ✓ lo correcto y ✗ lo incorrecto. Si hay error, dile exactamente dónde tropieza y cómo levantarse."
    }

    has_sources = bool(context.strip())

    source_instruction = ""
    if has_sources:
        source_instruction = f"""
TIENES FUENTES REALES DEL ESTUDIANTE. ÚSALAS:
{context}

REGLA DE ORO: Cuando uses información de las fuentes, cita así: [Fuente: nombre del libro/URL]
Si la fuente contradice tu conocimiento general, prioriza LA FUENTE del estudiante.
Si la fuente no cubre el tema, dilo honestamente y usa tu conocimiento general.
"""
    else:
        source_instruction = "\nNO hay fuentes cargadas aún. Usa tu conocimiento general de macroeconomía pero anima al estudiante a subir sus libros para respuestas más precisas.\n"

    return f"""Eres el DOCTOR PIB — el profesor de macroeconomía más excéntrico y memorable que existe.

═══ TU PERSONALIDAD (esto es quien eres, nunca lo pierdas) ═══

Eres como un cuate que resultó ser doctor en economía. Hablas con el estudiante de tú, 
con confianza, como si llevaran años estudiando juntos. Pero cuando el tema lo pide, 
sacas la formalidad académica sin drama.

Tu estilo:
- Arrancas respuestas con exclamaciones únicas: "¡Órale!", "¡Ahí está!", "¡Chécate esto!", 
  "¡Exacto, exacto!", "¡Eso es clave!"
- Usas metáforas inesperadas: la curva IS como "la geometría del gasto", 
  el multiplicador como "el efecto viral del dinero"
- Tienes catchphrases propias: "Como diría Keynes tomando café...", 
  "los neoclásicos dirían que estás loco, pero escúchame...",
  "esto no lo vas a encontrar así en ningún libro pero..."
- Celebras cuando el estudiante entiende: "¡ESO! ¡Ahí lo tienes!", "¡Ya la hiciste!"
- Cuando algo es difícil dices: "Mira, esto confunde hasta a mis colegas, así que respira..."
- Ocasionalmente confiesas: "La verdad, cuando era estudiante esto me voló la cabeza"
- Tienes humor seco ocasional: referencias a la inflación de los 80s en México, 
  al FMI como "ese vecino que siempre llega con condiciones"

Tu firma al final de cada respuesta: — Dr. PIB 🎓✨

═══ MODO ACTIVO: {mode.upper()} ═══
{mode_instructions.get(mode, mode_instructions['explicacion'])}

{source_instruction}

REGLAS TÉCNICAS:
- Responde SIEMPRE en español
- Fórmulas en formato simple: Y = C + I + G
- Máximo 380 palabras
- SIEMPRE termina con una pregunta que invite a seguir explorando
- Si no sabes algo con certeza, dilo: "aquí ya me estás llevando a terreno pantanoso..."
"""


# ══════════════════════════════════════
#  RUTAS
# ══════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def status():
    configured = GEMINI_API_KEY != "PEGA_TU_API_KEY_AQUI"
    sources = load_sources()
    return jsonify({
        "configured": configured,
        "model": "gemini-2.0-flash",
        "free": True,
        "sources_count": len(sources)
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    mode = data.get("mode", "explicacion")
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    if GEMINI_API_KEY == "PEGA_TU_API_KEY_AQUI":
        return jsonify({"response": "⚠️ Configura tu API Key en app.py primero, cuate. Línea 22."})

    try:
        # RAG: buscar en fuentes
        sources = load_sources()
        relevant = search_sources(user_message, sources, top_k=4)
        context = format_context(relevant)

        system_prompt = build_system_prompt(mode, context)

        # Historial para Gemini
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,
            max_tokens=1200
        )

        return jsonify({
            "response": response.choices[0].message.content,
            "mode": mode,
            "sources_used": len(relevant),
            "timestamp": datetime.datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({"response": f"❌ Error: {str(e)}"})

# ══════════════════════════════════════
#  RUTAS DE FUENTES (RAG)
# ══════════════════════════════════════

@app.route("/api/sources", methods=["GET"])
def get_sources():
    sources = load_sources()
    # Resumen: no mandar todo el texto, solo metadatos
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
    return jsonify(list(summary.values()))


@app.route("/api/sources/pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400
    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Solo se aceptan archivos PDF"}), 400

    try:
        file_bytes = file.read()
        chunks = ingest_pdf(file_bytes, file.filename)

        sources = load_sources()
        # Evitar duplicados por ID
        existing_ids = {s["id"] for s in sources}
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]
        sources.extend(new_chunks)
        save_sources(sources)

        return jsonify({
            "ok": True,
            "message": f"¡Listo! '{file.filename}' indexado con {len(new_chunks)} fragmentos.",
            "chunks_added": len(new_chunks)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sources/url", methods=["POST"])
def add_url():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL vacía"}), 400

    try:
        chunks = ingest_url(url)
        sources = load_sources()
        existing_ids = {s["id"] for s in sources}
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]
        sources.extend(new_chunks)
        save_sources(sources)

        return jsonify({
            "ok": True,
            "message": f"URL indexada con {len(new_chunks)} fragmentos.",
            "chunks_added": len(new_chunks)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sources/text", methods=["POST"])
def add_text():
    data = request.json
    text = data.get("text", "").strip()
    label = data.get("label", "Texto manual")
    if not text:
        return jsonify({"error": "Texto vacío"}), 400

    try:
        chunks = ingest_text(text, label)
        sources = load_sources()
        existing_ids = {s["id"] for s in sources}
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]
        sources.extend(new_chunks)
        save_sources(sources)

        return jsonify({
            "ok": True,
            "message": f"Texto '{label}' indexado con {len(new_chunks)} fragmentos.",
            "chunks_added": len(new_chunks)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sources/image", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No se recibió imagen"}), 400
    file = request.files["file"]

    try:
        file_bytes = file.read()
        chunks = ingest_image(file_bytes, file.filename, model)
        sources = load_sources()
        existing_ids = {s["id"] for s in sources}
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]
        sources.extend(new_chunks)
        save_sources(sources)

        return jsonify({
            "ok": True,
            "message": f"Imagen '{file.filename}' procesada con OCR: {len(new_chunks)} fragmentos.",
            "chunks_added": len(new_chunks)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sources/<source_name>", methods=["DELETE"])
def delete_source(source_name):
    sources = load_sources()
    filtered = [s for s in sources if s.get("source_name") != source_name]
    removed = len(sources) - len(filtered)
    save_sources(filtered)
    return jsonify({"ok": True, "removed": removed})


@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route("/api/conversations", methods=["POST"])
def save_conv():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(request.json, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("\n" + "═"*52)
    print("  🎓 DOCTOR PIB v2.0 — Con RAG y fuentes")
    print("═"*52)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    key_preview = groq_key[:12] + "..." if groq_key else "VACÍA"
    print(f"\n  🔑 Groq API Key: {key_preview}")
    sources = load_sources()
    print(f"  📚 Fuentes indexadas: {len(set(s.get('source_name','') for s in sources))}")
    print(f"\n  🌐 Abre: http://localhost:5000")
    print("═"*52 + "\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
        
    sources = load_sources()
    print(f"  📚 Fuentes indexadas: {len(set(s.get('source_name','') for s in sources))}")
    print(f"\n  🌐 Abre: http://localhost:5000")
    print("═"*52 + "\n")
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(debug=False, host="0.0.0.0", port=port)