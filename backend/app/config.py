"""Paths and global settings for Al Basmah AI Media Studio."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("STUDIO_DATA_DIR", ROOT / "data")).resolve()
ORIGINALS = DATA_DIR / "originals"   # uploaded files, never modified (read-only)
META = DATA_DIR / "meta"             # one JSON per uploaded file
THUMBS = DATA_DIR / "thumbs"
OUTPUTS = DATA_DIR / "outputs"       # one folder per job
WORK = DATA_DIR / "work"             # temporary intermediates
JOBS = DATA_DIR / "jobs"
SETTINGS_FILE = DATA_DIR / "settings.json"
FRONTEND = ROOT / "frontend"
FONTS = ROOT / "assets" / "fonts"
FONT_BOLD = str(FONTS / "Cairo-700.ttf")
FONT_REGULAR = str(FONTS / "Cairo-400.ttf")

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")
MAX_WORKERS = int(os.environ.get("STUDIO_WORKERS", "2"))
PASSWORD = os.environ.get("STUDIO_PASSWORD", "")  # optional basic-auth password

GOLD = (212, 175, 55)
BLACK = (10, 10, 10)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".heic", ".heif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".3gp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

for d in (ORIGINALS, META, THUMBS, OUTPUTS, WORK, JOBS):
    d.mkdir(parents=True, exist_ok=True)
