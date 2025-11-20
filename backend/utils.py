import os
from typing import List, Union

# Document parsing libraries
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def ensure_directories(paths: List[str]) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def save_upload_temporarily(upload, dest_dir: str) -> str:
    """Save uploaded file temporarily. Works with Django's UploadedFile."""
    os.makedirs(dest_dir, exist_ok=True)
    filename = getattr(upload, 'name', None) or getattr(upload, 'filename', None) or "upload.bin"
    dest = os.path.join(dest_dir, filename)
    # If exists, create a unique variant
    base, ext = os.path.splitext(dest)
    i = 1
    while os.path.exists(dest):
        dest = f"{base}_{i}{ext}"
        i += 1
    with open(dest, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)
    return dest


def read_pdf(path: str) -> str:
    """Extract text from PDF file."""
    if not HAS_PDF:
        print("PDF: PyPDF2 not installed, skipping PDF parsing")
        return ""
    
    try:
        text = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        result = "\n\n".join(text)
        print(f"PDF: Extracted {len(result)} characters from {len(text)} pages")
        return result
    except Exception as e:
        print(f"PDF: Failed to parse {path}: {e}")
        return ""


def read_docx(path: str) -> str:
    """Extract text from DOCX file."""
    if not HAS_DOCX:
        print("DOCX: python-docx not installed, skipping DOCX parsing")
        return ""
    
    try:
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs)
        print(f"DOCX: Extracted {len(result)} characters from {len(paragraphs)} paragraphs")
        return result
    except Exception as e:
        print(f"DOCX: Failed to parse {path}: {e}")
        return ""


def read_text_file(path: str) -> str:
    """Read text from various file formats with proper parsing."""
    filename_lower = path.lower()
    
    # PDF files
    if filename_lower.endswith(".pdf"):
        return read_pdf(path)
    
    # DOCX files
    elif filename_lower.endswith(".docx"):
        return read_docx(path)
    
    # Plain text files
    elif filename_lower.endswith(".txt"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            print(f"TXT: Read {len(content)} characters")
            return content
        except Exception as e:
            print(f"TXT: Failed to read {path}: {e}")
            return ""
    
    # Unknown format
    else:
        print(f"Unknown file format: {path}")
        return ""



