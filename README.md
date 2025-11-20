# AI Study Tutor

Django-powered AI study assistant with RAG (Retrieval Augmented Generation), multi-modal input support, and intelligent document processing.

## Features

- **🤖 Advanced AI Chat** - Context-aware responses using Groq's LLaMA models
- **📚 Smart Document Processing** - Automatic text extraction from PDFs, DOCX, and plain text files
- **🔍 Semantic Search** - Real embeddings with sentence-transformers for accurate knowledge retrieval
- **🎤 Voice Support** - Audio transcription and text-to-speech with multiple voices
- **🖼️ Image OCR** - Extract text from images and handwritten notes
- **💾 Persistent Sessions** - SQLite-backed conversation history
- **🎨 Modern UI** - Clean, responsive interface with markdown and LaTeX support

## Quickstart

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

**Note:** First install may take a few minutes as it downloads the sentence-transformers model (~80MB).

### 2. Configure environment

Create a `.env` file:

```bash
copy .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=your-groq-api-key-here
```

Get your free API key at https://console.groq.com/

### 3. Run the server

```bash
python manage.py runserver 0.0.0.0:8000
```

### 4. Open the app

Visit `http://localhost:8000` or `http://localhost:8000/static/chat.html`

## API Endpoints

- `POST /send-message` - Send a chat message
- `POST /upload-file` - Upload documents, images, or audio (max 50MB)
- `POST /generate-tts` - Generate text-to-speech for messages
- `POST /transcribe` - Transcribe audio files
- `GET /history?session_id=...` - Retrieve conversation history
- `POST /reset-history` - Clear session history
- `POST /reset-index` - Clear knowledge base
- `GET /healthz` - Health check

## Supported File Types

- **Documents:** PDF, DOCX, TXT
- **Images:** PNG, JPG, JPEG (OCR with vision model)
- **Audio:** WEBM, WAV, MP3, M4A, OGG (Whisper transcription)

## Technology Stack

- **Backend:** Django 4.2 + Django REST Framework
- **AI Models:** 
  - LLM: Groq `llama-3.3-70b-versatile` / `openai/gpt-oss-120b` (reasoning)
  - STT: Groq `whisper-large-v3`
  - Vision: `meta-llama/llama-4-scout-17b-16e-instruct`
  - TTS: PlayAI TTS (6 voice options)
- **Embeddings:** sentence-transformers `all-MiniLM-L6-v2`
- **Vector Store:** FAISS with cosine similarity
- **Database:** SQLite
- **Document Parsing:** PyPDF2, python-docx

## Configuration

### Settings (via `.env` or environment variables)

- `GROQ_API_KEY` - Required for AI features
- `DJANGO_SECRET_KEY` - Django secret (auto-generated for dev)

### Voice Options

Available TTS voices: Gail-PlayAI, Fritz-PlayAI, Arista-PlayAI, Atlas-PlayAI, Quinn-PlayAI, Thunder-PlayAI

### Reasoning Mode

Enable detailed step-by-step reasoning by:
1. Clicking the settings gear icon
2. Checking "Detailed reasoning"
3. This uses a more powerful model for complex problems

## Data Storage

- `data/sessions.sqlite3` - Chat history and sessions
- `data/audio/` - Generated TTS audio files
- `data/uploads/` - Uploaded documents and files
- `data/index/` - FAISS vector index and metadata

## Troubleshooting

**"No module named 'sentence_transformers'"**
- Run `pip install sentence-transformers`
- The model will download automatically on first use

**"Failed to extract text from PDF"**
- Ensure PyPDF2 is installed: `pip install PyPDF2`
- Some PDFs with complex layouts may not parse perfectly

**"TTS failed"**
- Check your GROQ_API_KEY is set correctly
- Verify API quota at https://console.groq.com/

**RAG not finding relevant documents**
- Clear and rebuild the index: POST to `/reset-index`
- Re-upload your documents to re-index with real embeddings

## Development

This is a production-ready prototype with:
- ✅ Real semantic embeddings (not dummy placeholders)
- ✅ Proper PDF/DOCX parsing
- ✅ Comprehensive error handling
- ✅ Input validation and file size limits
- ✅ Detailed logging for debugging

For production deployment, consider:
- Setting `DEBUG=False` in settings
- Using a production WSGI server (gunicorn, uWSGI)
- Adding user authentication if needed
- Configuring proper ALLOWED_HOSTS

## License

Prototype for educational purposes.
