import os
import base64
from typing import List, Optional
import requests


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")


def generate_text_with_context(query: str, retrieved_snippets: Optional[List[str]] = None, use_reasoning: bool = False) -> str:
    if not GROQ_API_KEY:
        # Fallback if no key set
        return (
            "Here's a concise, helpful response. Upload notes or a PDF to tailor the answer "
            "and build a focused study plan."
        )

    system_prompt = """You are AI Study Tutor. Provide accurate, step-by-step help for studying and problem solving.
    Focus on accuracy, clarity, and helpful guidance. Do not worry about visual formatting.
    """
    context_blocks = [f"[Context {i+1}]\n{snip}" for i, snip in enumerate(retrieved_snippets or [])]
    user_content = query if not context_blocks else f"{query}\n\n\n{chr(10).join(context_blocks)}"

    try:
        model_id = "openai/gpt-oss-120b" if use_reasoning else "llama-3.3-70b-versatile"
        resp = requests.post(
            f"{GROQ_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Sorry, something went wrong while generating the response."


def transcribe_audio(audio_path: str) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "application/octet-stream")}
            data = {"model": "whisper-large-v3", "language": "en"}
            resp = requests.post(
                f"{GROQ_API_BASE}/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                data=data,
                files=files,
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
    except Exception:
        return ""


def extract_text_from_image(image_path: str) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        # OpenAI-compatible vision via chat.completions with image_url data URL
        system_prompt = (
            "You are an OCR and vision assistant. Extract all legible text and math from the image. "
            "Return plain text only; preserve important structure like line breaks and lists."
        )
        data_url = f"data:image/{os.path.splitext(image_path)[1].lstrip('.').lower()};base64,{b64}"
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract all text from this image."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]},
            ],
        }
        resp = requests.post(
            f"{GROQ_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


