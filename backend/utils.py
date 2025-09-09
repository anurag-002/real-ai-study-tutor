import os
from typing import List
from fastapi import UploadFile


def ensure_directories(paths: List[str]) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


async def save_upload_temporarily(upload: UploadFile, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    filename = upload.filename or "upload.bin"
    dest = os.path.join(dest_dir, filename)
    # If exists, create a unique variant
    base, ext = os.path.splitext(dest)
    i = 1
    while os.path.exists(dest):
        dest = f"{base}_{i}{ext}"
        i += 1
    with open(dest, "wb") as f:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return dest


def read_text_file(path: str) -> str:
    # naive; for PDF/DOCX you would parse; here we just read plain text
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


