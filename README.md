# AI Study Tutor (Prototype)

FastAPI backend + minimal static frontend for a study assistant with RAG.

Note: All models use Groq API (set GROQ_API_KEY).

## Quickstart

1. Create and activate a virtualenv (Windows PowerShell):

```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

2. Set environment variables (optional):

```
setx GROQ_API_KEY "your_key_here"
```

3. Run the server:

```
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Open the app:

- Visit `http://localhost:8000/static/index.html`

## Endpoints

- POST `/send-message`
- POST `/upload-file`
- GET `/history?session_id=...`
- POST `/reset-history`

## Data

- `data/sessions.sqlite3` stores messages
- `data/audio` stores generated audio files
- `data/uploads` stores uploaded files
- `data/index` holds FAISS index (simple in-memory placeholder)

## Integrations (to replace placeholders)

- LLM: Groq `llama-3.3-70b-versatile`
- STT: Groq `whisper-large-v3`
- Vision: `meta-llama/llama-4-scout-17b-16e-instruct`
- TTS: `playai-tts`

Real API calls are implemented in `backend/groq_client.py` and `backend/tts.py`.

Note: FAISS is included by default with NumPy 1.26.x pin for compatibility. On Windows, prebuilt FAISS wheels are limited; WSL or Linux is recommended for production FAISS.
