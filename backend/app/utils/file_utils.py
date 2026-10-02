import os
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 50

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_file(filename: str, size_bytes: int):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")
    if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File too large. Max {MAX_FILE_SIZE_MB}MB allowed.")
    return ext


def safe_save(file_bytes: bytes, original_filename: str, paper_id: int) -> str:
    ext = Path(original_filename).suffix.lower()
    safe_name = f"{paper_id}_{uuid.uuid4().hex}{ext}"
    paper_dir = UPLOAD_DIR / str(paper_id)
    paper_dir.mkdir(parents=True, exist_ok=True)
    filepath = paper_dir / safe_name
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    return str(filepath)