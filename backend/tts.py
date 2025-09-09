import os
import hashlib
import requests
from typing import Optional

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")


def hash_audio_filename(text: str, voice: str) -> str:
    key = f"{voice}|{text}".encode("utf-8", errors="ignore")
    return hashlib.sha256(key).hexdigest()


def synthesize_tts(text: str, output_path: str, voice: str = "Gail-PlayAI") -> Optional[str]:
    print(f"=== TTS CALLED === Text: '{text[:30]}...', Voice: {voice}, Path: {output_path}")
    # Cache: if file already exists, skip synthesis
    try:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 3:
            print("TTS: Using cached audio file")
            return output_path
    except Exception:
        pass
    if not GROQ_API_KEY:
        print("TTS: No API key, using fallback")
        # Fallback: create a minimal audio file placeholder
        with open(output_path, "wb") as f:
            f.write(b"ID3")
        return output_path

    try:
        print(f"TTS: Attempting to synthesize '{text[:50]}...' with Gail-PlayAI")
        print(f"TTS: API Key present: {bool(GROQ_API_KEY)}")
        print(f"TTS: API Base: {GROQ_API_BASE}")
        
        # Use Groq TTS endpoint with correct parameters
        response = requests.post(
            f"{GROQ_API_BASE}/audio/speech",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "playai-tts",
                "input": text,
                "voice": voice,
                "response_format": "wav"  # Default format, not mp3
            },
            timeout=60,
        )
        
        print(f"TTS: Response status: {response.status_code}")
        print(f"TTS: Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"TTS error: {response.text}")
            raise Exception(f"TTS API returned {response.status_code}: {response.text}")
        
        # Save the audio data to file
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        print(f"TTS success: saved {len(response.content)} bytes to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"TTS synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: create placeholder file
        with open(output_path, "wb") as f:
            f.write(b"ID3")
        return output_path


