import os
import io
import sys
import re
from pathlib import Path
from PIL import Image


# Resource Loader
def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        base_path = Path(__file__).parent
    else:
        base_path = Path(base_path)
    return str(base_path / relative_path)

def find_resource(relative_path: str) -> Path | None:
    base = (
        Path(getattr(sys, "_MEIPASS", None))
        if getattr(sys, "_MEIPASS", None)
        else Path(__file__).parent
    )
    requested = Path(relative_path)
    candidate = base / requested
    if candidate.exists():
        return candidate
    target_name = requested.name.lower()
    try:
        for p in base.rglob("*"):
            if p.is_file() and p.name.lower() == target_name:
                return p
    except Exception:
        pass
    def normalize(s: str) -> str:
        s2 = re.sub(r"[\s\-_]+", "", s.lower())
        return re.sub(r"[^a-z0-9]", "", s2)
    target_norm = normalize(requested.name)
    try:
        for p in base.rglob("*"):
            if p.is_file() and normalize(p.name) == target_norm:
                return p
    except Exception:
        pass
    return None


# Time Formatter
def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


# Album Art Extractor
def extract_album_art(file_path):
    from mutagen.id3 import ID3, APIC
    try:
        audio = ID3(file_path)
        for tag in audio.values():
            if isinstance(tag, APIC):
                return Image.open(io.BytesIO(tag.data))
    except Exception:
        pass
    return None


# Track Name Shortener
def shorten_name(name, max_len=36):
    if not isinstance(name, str):
        name = str(name)
    if len(name) <= max_len:
        return name
    base, ext = os.path.splitext(name)
    if ext and len(ext) <= 6 and len(base) > (max_len - 4 - len(ext)):
        return base[:max_len - 4 - len(ext)] + "..." + ext
    return name[:max_len - 3] + "..."
