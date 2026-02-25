# 🎓 DOCTOR PIB — Guía de Instalación

## PASO 1 — Abre la carpeta en Visual Studio Code

1. Abre Visual Studio Code
2. Clic en **Archivo → Abrir carpeta**
3. Selecciona la carpeta `doctor_pib`

---

## PASO 2 — Instala las librerías (solo una vez)

Abre la **Terminal** en VS Code:
- Menú → Terminal → Nueva Terminal
- O presiona `Ctrl + Ñ` (o `Ctrl + backtick`)

Escribe este comando y presiona Enter:

```
pip install flask flask-cors google-generativeai
```

Espera que termine (1-2 minutos).

---

## PASO 3 — Consigue tu API Key de Gemini (GRATIS)

1. Ve a: **https://aistudio.google.com**
2. Entra con tu cuenta de Google (Gmail)
3. Clic en **"Get API Key"** (esquina superior izquierda)
4. Clic en **"Create API key"**
5. Selecciona "Create API key in new project"
6. Copia la clave (empieza con `AIza...`)

---

## PASO 4 — Pega tu API Key en el código

1. Abre el archivo `app.py` en VS Code
2. Busca esta línea (línea ~22):
   ```
   GEMINI_API_KEY = "PEGA_TU_API_KEY_AQUI"
   ```
3. Reemplaza `PEGA_TU_API_KEY_AQUI` con tu clave real:
   ```
   GEMINI_API_KEY = "AIzaSy...tu_clave_aqui..."
   ```
4. Guarda el archivo: `Ctrl + S`

---

## PASO 5 — Ejecuta el servidor

En la terminal de VS Code escribe:
```
python app.py
```

Verás este mensaje:
```
══════════════════════════════════════════════════
  🎓 DOCTOR PIB — Iniciando servidor...
══════════════════════════════════════════════════
  ✅ API Key configurada correctamente
  🌐 Abre en tu navegador:
     http://localhost:5000
```

---

## PASO 6 — Abre el chatbot

1. Abre tu navegador (Chrome, Edge, Firefox)
2. Ve a: **http://localhost:5000**
3. ¡Listo! El Doctor PIB está funcionando 🎓

---

## 🔄 Para usar el chatbot la próxima vez

Solo necesitas:
1. Abrir VS Code
2. Abrir la carpeta `doctor_pib`
3. Abrir la terminal y escribir: `python app.py`
4. Ir a http://localhost:5000

---

## ❓ Preguntas frecuentes

**¿Se borra la memoria al cerrar?**
No. Las conversaciones se guardan automáticamente en el navegador (localStorage).

**¿Cuánto cuesta Gemini?**
El plan gratuito te da 1,000 preguntas por día. Para un estudiante es más que suficiente.

**¿Puedo subir PDFs de mis libros?**
En esta versión básica no, pero puedes describir el contenido y el Doctor PIB te ayuda.

**¿Cómo paro el servidor?**
En la terminal presiona `Ctrl + C`

---

## 📁 Estructura del proyecto

```
doctor_pib/
├── app.py              ← Servidor Python (aquí va tu API Key)
├── requirements.txt    ← Librerías necesarias
├── conversations.json  ← Se crea automáticamente (historial)
├── README.md           ← Esta guía
└── static/
    └── index.html      ← Interfaz del chatbot
```
