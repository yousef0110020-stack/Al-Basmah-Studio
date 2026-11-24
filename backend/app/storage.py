"""Upload storage. Originals are written once and made read-only; nothing edits them."""
import json
import os
import shutil
import stat
import subprocess
import time
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from . import config
from .imageio import load_image

try:
    import pillow_heif  # iPhone HEIC support
    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pass


def kind_for(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in config.IMAGE_EXT:
        return "image"
    if ext in config.VIDEO_EXT:
        return "video"
    if ext in config.AUDIO_EXT:
        return "audio"
    return "other"


def ffprobe(path: str) -> dict:
    out = subprocess.run(
        [config.FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def video_info(path: str) -> dict:
    p = ffprobe(path)
    v = next((s for s in p["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    dur = float(p["format"].get("duration") or (v or {}).get("duration") or 0)
    info = {"duration": round(dur, 3), "has_audio": a is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        rot = int(v.get("tags", {}).get("rotate", rot))
        if abs(rot) in (90, 270):
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or "30/1").split("/")
        fps = float(num) / float(den) if float(den) else 30.0
        info.update(width=w, height=h, fps=round(fps, 3), codec=v.get("codec_name"),
                    color_transfer=v.get("color_transfer"), pix_fmt=v.get("pix_fmt"))
    return info


def save_upload(src_fileobj, filename: str, role: str | None = None) -> dict:
    fid = uuid.uuid4().hex[:12]
    ext = Path(filename).suffix.lower() or ".bin"
    dest = config.ORIGINALS / f"{fid}{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(src_fileobj, f, length=1024 * 1024)
    os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # read-only original
    meta = {"id": fid, "name": filename, "kind": kind_for(filename), "ext": ext,
            "size": dest.stat().st_size, "created": time.time()}
    if role == "logo":
        meta["role"] = "logo"
    try:
        if meta["kind"] == "image":
            im = load_image(str(dest))
            meta.update(width=im.width, height=im.height)
            t = im.copy()
            t.thumbnail((480, 480))
            t.convert("RGB").save(config.THUMBS / f"{fid}.jpg", quality=85)
        elif meta["kind"] == "video":
            meta.update(video_info(str(dest)))
            ss = min(1.0, meta.get("duration", 0) / 2)
            subprocess.run([config.FFMPEG, "-y", "-v", "error", "-ss", str(ss), "-i", str(dest), "-frames:v", "1",
                            "-vf", "scale=480:-2", str(config.THUMBS / f"{fid}.jpg")], check=False)
        elif meta["kind"] == "audio":
            p = ffprobe(str(dest))
            meta["duration"] = round(float(p["format"].get("duration") or 0), 3)
    except Exception as e:  # keep the upload, report the problem
        meta["error"] = f"could not read file: {e}"
    (config.META / f"{fid}.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


def get_meta(fid: str) -> dict:
    p = config.META / f"{fid}.json"
    if not fid.isalnum() or not p.exists():
        raise KeyError(fid)
    return json.loads(p.read_text())


def original_path(fid: str) -> str:
    m = get_meta(fid)
    return str(config.ORIGINALS / f"{fid}{m['ext']}")


def list_files(kind: str | None = None) -> list:
    items = []
    for p in config.META.glob("*.json"):
        m = json.loads(p.read_text())
        if (kind is None or m["kind"] == kind) and not (kind and m.get("role") == "logo"):
            items.append(m)
    return sorted(items, key=lambda m: m["created"], reverse=True)


def load_settings() -> dict:
    if config.SETTINGS_FILE.exists():
        return json.loads(config.SETTINGS_FILE.read_text())
    return {}


def save_settings(s: dict) -> dict:
    config.SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))
    return s
