import os
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse, Response, FileResponse

from .models import SendMessageRequest, SendMessageResponse, UploadFileResponse, HistoryResponse, ResetHistoryRequest
from .db import init_db, append_message, get_history, reset_history_if_exists, ensure_session
from .rag import get_or_create_index, search_similar_snippets, upsert_documents, clear_index
from .groq_client import generate_text_with_context, transcribe_audio, extract_text_from_image
from .tts import synthesize_tts
from .utils import ensure_directories, save_upload_temporarily, read_text_file


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_ROOT)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
INDEX_DIR = os.path.join(DATA_DIR, "index")


ensure_directories([DATA_DIR, STATIC_DIR, UPLOADS_DIR, AUDIO_DIR, INDEX_DIR])
init_db(os.path.join(DATA_DIR, "sessions.sqlite3"))

app = FastAPI(title="AI Study Tutor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend and generated audio files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.post("/send-message", response_model=SendMessageResponse)
async def send_message(request: Request, data: SendMessageRequest):
    session_id = data.session_id or str(uuid.uuid4())
    ensure_session(session_id)
    
    user_text = data.content
    print(f"MAIN: Processing message: '{user_text[:50]}...'")
    
    # Generate AI response
    try:
        # Check if reasoning model should be used
        use_reasoning = request.headers.get("x-reasoning") or request.headers.get("X-Reasoning")
        use_reasoning = use_reasoning and use_reasoning.lower() in ("true", "1", "yes")
        
        reply_text = generate_text_with_context(user_text, use_reasoning=use_reasoning)
        print(f"MAIN: Generated reply: '{reply_text[:50]}...'")
    except Exception as e:
        print(f"MAIN: Text generation failed: {e}")
        import traceback
        traceback.print_exc()
        # graceful fallback
        reply_text = "Sorry, something went wrong while processing your request."

    # Save to history (no TTS by default)
    ts = now_iso()
    append_message(session_id, sender="user", content=user_text, audio_url=None, timestamp=ts)
    append_message(session_id, sender="ai", content=reply_text, audio_url=None, timestamp=ts)

    return SendMessageResponse(
        session_id=session_id,
        reply_text=reply_text,
        reply_audio_url=None,  # No automatic TTS
        timestamp=ts,
    )


@app.post("/generate-tts")
async def generate_tts(request: Request):
    """Generate TTS for a specific message on demand"""
    data = await request.json()
    message_id = data.get("message_id")
    voice = request.headers.get("x-voice") or request.headers.get("X-Voice") or "Gail-PlayAI"
    
    if not message_id:
        return {"error": "message_id required"}
    
    # Get the message content from database
    # For now, we'll accept the text directly
    text = data.get("text")
    if not text:
        return {"error": "text required"}
    
    try:
        audio_filename = f"tts_{int(time.time())}.wav"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        print(f"MAIN: Generating TTS for '{text[:30]}...' with voice {voice}")
        synthesize_tts(text, audio_path, voice=voice)
        audio_rel_url = f"/audio/{audio_filename}"
        print(f"MAIN: TTS completed, audio URL: {audio_rel_url}")
        
        return {
            "success": True,
            "audio_url": audio_rel_url
        }
    except Exception as e:
        print(f"MAIN: TTS failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@app.post("/upload-file", response_model=UploadFileResponse)
async def upload_file(request: Request, session_id: Optional[str] = Form(None), user_note: Optional[str] = Form(None), file: UploadFile = File(...)):
    session_id = session_id or str(uuid.uuid4())
    ensure_session(session_id)

    # Save upload to disk
    temp_path = await save_upload_temporarily(file, UPLOADS_DIR)

    # Determine handling based on content type / extension
    filename_lower = file.filename.lower() if file.filename else ""
    text_content: Optional[str] = None

    try:
        if filename_lower.endswith((".pdf", ".docx", ".txt")):
            text_content = read_text_file(temp_path)
        elif filename_lower.endswith((".png", ".jpg", ".jpeg")):
            # Vision model to extract problem text
            try:
                text_content = extract_text_from_image(temp_path)
            except Exception:
                text_content = None
        elif filename_lower.endswith((".webm", ".wav", ".mp3", ".m4a", ".ogg")):
            # Transcribe audio to text
            try:
                text_content = transcribe_audio(temp_path)
            except Exception:
                text_content = None
        else:
            text_content = None

        is_audio = filename_lower.endswith((".webm", ".wav", ".mp3", ".m4a", ".ogg"))
        is_doc = filename_lower.endswith((".pdf", ".docx", ".txt"))

        # For transcribed audio: treat transcription as a user message (do not ingest)
        if is_audio and text_content and text_content.strip():
            user_text = text_content.strip()
            # Merge optional user note
            query_text = f"{user_note.strip()}\n\n{user_text}" if user_note else user_text
            index = get_or_create_index(INDEX_DIR)
            retrieved = search_similar_snippets(index=index, query_text=query_text, k=3)
            try:
                use_reasoning = (request.headers.get("X-Reasoning", "").lower() == "true")
                reply_text = generate_text_with_context(query=query_text, retrieved_snippets=retrieved, use_reasoning=use_reasoning)
            except Exception:
                reply_text = "Sorry, something went wrong while processing your request."
            ts = now_iso()
            if user_note and user_note.strip():
                append_message(session_id, sender="user", content=user_note.strip(), audio_url=None, timestamp=ts)
            append_message(session_id, sender="user", content=user_text, audio_url=None, timestamp=ts)
        else:
            # Ingest documents/images with extracted text
            if is_doc and text_content and text_content.strip():
                index = get_or_create_index(INDEX_DIR)
                upsert_documents(index=index, docs=[{"session_id": session_id, "text": text_content, "source": filename_lower or "upload"}])

            # Prepare helpful AI confirmation response about the uploaded file
            base_prompt = f"A new study document was uploaded. Provide a helpful brief summary and suggest how to study it.\nSource: {file.filename}"
            user_prompt = f"{user_note.strip()}\n\n{base_prompt}" if user_note else base_prompt
            retrieved = []
            if text_content:
                retrieved = [text_content[:1200]]
            try:
                use_reasoning = (request.headers.get("X-Reasoning", "").lower() == "true")
                reply_text = generate_text_with_context(query=user_prompt, retrieved_snippets=retrieved, use_reasoning=use_reasoning)
            except Exception:
                reply_text = "Sorry, something went wrong while processing your request."
            ts = now_iso()
            label = "audio" if is_audio else "file"
            if user_note and user_note.strip():
                append_message(session_id, sender="user", content=user_note.strip(), audio_url=None, timestamp=ts)
            append_message(session_id, sender="user", content=f"[Uploaded {label}] {file.filename}", audio_url=None, timestamp=ts)

        # No automatic TTS here; generate on demand via /generate-tts
        append_message(session_id, sender="ai", content=reply_text, audio_url=None, timestamp=ts)

        return UploadFileResponse(
            session_id=session_id,
            reply_text=reply_text,
            reply_audio_url=None,
            timestamp=ts,
        )
    finally:
        # We keep the original uploaded file for future reference in uploads dir
        pass


@app.get("/history", response_model=HistoryResponse)
async def get_session_history(session_id: str):
    ensure_session(session_id)
    messages = get_history(session_id)
    return HistoryResponse(session_id=session_id, messages=messages)


@app.post("/reset-history")
async def reset_history(payload: ResetHistoryRequest):
    if not payload.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    reset_history_if_exists(payload.session_id)
    return JSONResponse({"success": True})


@app.post("/reset-index")
async def reset_index():
    clear_index(INDEX_DIR)
    return JSONResponse({"success": True})


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribe audio only and return text without creating messages."""
    # Save upload
    temp_path = await save_upload_temporarily(file, UPLOADS_DIR)
    try:
        text = transcribe_audio(temp_path) or ""
        if not text:
            return JSONResponse({"text": ""})
        return JSONResponse({"text": text})
    finally:
        pass


# Health
@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/index.html", status_code=302)


@app.get("/favicon.ico")
async def favicon():
    # Avoid hanging requests for favicon; serve empty 204
    return Response(status_code=204)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)


