"""AI Auto Editor: measures each file (exposure, contrast, colour cast, noise, sharpness,
tilt, camera shake) and derives a style + editable settings from the measurements."""
import math
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import config
from .imageio import load_image
from .photo import auto_geometry, luminance
from .styles import photo_style, video_style


def noise_sigma(gray8: np.ndarray) -> float:
    """Immerkaer fast noise variance estimate (0..255 scale)."""
    h, w = gray8.shape
    M = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)
    conv = cv2.filter2D(gray8.astype(np.float32), -1, M)
    return float(np.sum(np.abs(conv[1:-1, 1:-1])) * math.sqrt(math.pi / 2) / (6 * (w - 2) * (h - 2)))


def image_stats(rgb8: np.ndarray, full_res_crop: np.ndarray | None = None) -> dict:
    h, w = rgb8.shape[:2]
    s = min(1.0, 1024 / max(h, w))
    small = cv2.resize(rgb8, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    a = small.astype(np.float32) / 255
    L = luminance(a)
    lab = cv2.cvtColor(a, cv2.COLOR_RGB2Lab)
    chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    mid = (lab[..., 0] > 15) & (lab[..., 0] < 92) & (chroma < 25)   # near-neutral pixels
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    gray_full = cv2.cvtColor(full_res_crop if full_res_crop is not None else small, cv2.COLOR_RGB2GRAY)
    return {
        "brightness": round(float(L.mean()), 3),
        "median": round(float(np.median(L)), 3),
        "p2": round(float(np.percentile(L, 2)), 3),
        "p98": round(float(np.percentile(L, 98)), 3),
        "contrast": round(float(L.std()), 3),
        "clipped_highlights": round(float((L > 0.98).mean() * 100), 2),
        "clipped_shadows": round(float((L < 0.02).mean() * 100), 2),
        "saturation": round(float(hsv[..., 1].mean() / 255), 3),
        "cast_a": round(float(lab[..., 1][mid].mean()) if mid.any() else 0.0, 2),
        "cast_b": round(float(lab[..., 2][mid].mean()) if mid.any() else 0.0, 2),
        "noise": round(noise_sigma(gray_full), 2),
        "sharpness": round(float(cv2.Laplacian(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var()), 1),
    }


def choose_style(st: dict) -> tuple[str, list]:
    reasons = []
    if st["median"] < 0.2 or st["brightness"] < 0.2:
        reasons.append({"ar": "الصورة داكنة جدًا (تصوير ليلي أو إضاءة ضعيفة)", "en": "Very dark image (night / low light)"})
        return "night", reasons
    reasons.append({"ar": "إضاءة كافية: نمط العقارات يعطي صورة واضحة ومشرقة بألوان حقيقية",
                    "en": "Adequate light: Real Estate style gives a bright, true-to-life result"})
    return "real_estate", reasons


def adapt_photo(style: str, st: dict, geo: dict | None) -> tuple[dict, list]:
    p = photo_style(style)
    notes = []
    target = 0.42
    ev = math.log2(target / max(st["median"], 0.02)) * 0.55
    ev = float(np.clip(ev, -0.6, 1.2))
    if abs(ev) > 0.08:
        p["exposure"] = round(ev + 0.3 * p["exposure"], 2)
        notes.append({"ar": f"تعديل التعريض {ev:+.2f} EV", "en": f"Exposure {ev:+.2f} EV"})
    if st["clipped_highlights"] > 1.5:
        p["highlights"] = min(p["highlights"], -0.55)
        notes.append({"ar": "استرجاع تفاصيل المناطق الساطعة (النوافذ والسماء)", "en": "Recover bright areas (windows/sky)"})
    if st["p2"] < 0.03:
        p["shadows"] = max(p["shadows"], 0.45)
        notes.append({"ar": "رفع تفاصيل الظلال", "en": "Lift shadow detail"})
    if abs(st["cast_a"]) > 2.5 or abs(st["cast_b"]) > 4:
        p["auto_wb"] = True
        notes.append({"ar": "تصحيح توازن الأبيض (يوجد ميل لوني)", "en": "White balance correction (colour cast found)"})
    n = st["noise"]
    if n > 3.0:  # texture (wood, stone) also raises the estimate, so stay conservative
        p["denoise"] = round(float(max(p["denoise"], np.clip((n - 3) / 8, 0.15, 0.7))), 2)
        p["sharpen"] = round(p["sharpen"] * 0.6, 2)
        notes.append({"ar": f"إزالة التشويش (مستوى الضوضاء {n})", "en": f"Noise reduction (noise level {n})"})
    if st["saturation"] < 0.15:
        p["vibrance"] = round(p["vibrance"] + 0.15, 2)
    elif st["saturation"] > 0.5:
        p["vibrance"] = round(p["vibrance"] - 0.15, 2)
        p["saturation"] = round(p["saturation"] - 0.05, 2)
    if st["contrast"] < 0.15:
        p["contrast"] = round(p["contrast"] + 0.08, 2)
    if geo and geo.get("confident"):
        p["rotate"], p["perspective_v"] = geo["rotate"], geo["perspective_v"]
        if geo["rotate"] or geo["perspective_v"]:
            notes.append({"ar": f"تصحيح الميلان {geo['rotate']}° والمنظور العمودي {geo['perspective_v']}",
                          "en": f"Straighten {geo['rotate']}° and vertical perspective {geo['perspective_v']}"})
    return p, notes


def analyze_photo(path: str, style: str | None = None) -> dict:
    im = load_image(path).convert("RGB")
    rgb8 = np.asarray(im)
    h, w = rgb8.shape[:2]
    c = 512
    crop = rgb8[max(0, h // 2 - c):h // 2 + c, max(0, w // 2 - c):w // 2 + c]
    st = image_stats(rgb8, crop)
    small = np.asarray(im.resize((min(w, 1600), int(h * min(w, 1600) / w))))
    geo = auto_geometry(small.astype(np.float32) / 255)
    auto_style, reasons = choose_style(st)
    used = style if style and style != "auto" else auto_style
    params, notes = adapt_photo(used, st, geo)
    return {"stats": st, "geometry": geo, "suggested_style": auto_style, "style": used,
            "reasons": reasons, "adjustments": notes, "params": params}


# ---------------------------------------------------------------- video

def _frames(path: str, duration: float, n=6, width=640) -> list:
    out = []
    with tempfile.TemporaryDirectory(dir=config.WORK) as td:
        for i in range(n):
            t = duration * (i + 0.5) / n
            f = Path(td) / f"f{i}.png"
            subprocess.run([config.FFMPEG, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                            "-vf", f"scale={width}:-2", str(f)], check=False)
            if f.exists():
                out.append(np.asarray(Image.open(f).convert("RGB")))
    return out


def shake_score(path: str, seconds=5.0) -> float:
    """Std-dev (px at 320 width) of high-frequency frame-to-frame motion."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    prev, d = None, []
    for _ in range(int(fps * seconds)):
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (320, int(g.shape[0] * 320 / g.shape[1]))).astype(np.float32)
        if prev is not None:
            (dx, dy), _ = cv2.phaseCorrelate(prev, g)
            d.append((dx, dy))
        prev = g
    cap.release()
    if len(d) < 10:
        return 0.0
    d = np.array(d)
    k = 9
    smooth = np.stack([np.convolve(d[:, i], np.ones(k) / k, mode="same") for i in range(2)], 1)
    jitter = (d - smooth)[k:-k]
    return round(float(np.sqrt((jitter ** 2).sum(1)).mean()), 3) if len(jitter) else 0.0


def analyze_video(path: str, info: dict, style: str | None = None) -> dict:
    frames = _frames(path, info.get("duration", 1))
    stats = [image_stats(f) for f in frames] or [image_stats(np.zeros((64, 64, 3), np.uint8))]
    st = {k: round(float(np.mean([s[k] for s in stats])), 3) for k in stats[0]}
    auto_style, reasons = choose_style(st)
    used = style if style and style != "auto" else auto_style
    p = video_style(used)
    notes = []
    gamma = float(np.clip(math.log(0.42) / math.log(max(st["median"], 0.03)), 0.8, 1.5))
    if abs(gamma - 1) > 0.04:
        p["gamma"] = round(p["gamma"] * gamma, 2) if used != "night" else round(max(p["gamma"], gamma), 2)
        notes.append({"ar": f"تصحيح الإضاءة (gamma {p['gamma']})", "en": f"Exposure correction (gamma {p['gamma']})"})
    if st["noise"] > 2.5:
        p["denoise"] = round(float(max(p["denoise"], np.clip((st["noise"] - 2) / 6, 0.2, 0.8))), 2)
        notes.append({"ar": "تقليل تشويش الصورة", "en": "Video noise reduction"})
    if abs(st["cast_b"]) > 5:
        p["warmth"] = round(p["warmth"] - np.clip(st["cast_b"] / 25, -0.6, 0.6), 2)
        notes.append({"ar": "موازنة حرارة الألوان", "en": "Colour temperature balance"})
    shake = shake_score(path)
    stabilize = shake > 0.6
    if stabilize:
        notes.append({"ar": f"يوجد اهتزاز في التصوير ({shake}) - يُنصح بالتثبيت", "en": f"Camera shake detected ({shake}) - stabilise"})
    p["stabilize"] = stabilize
    p["denoise_audio"] = bool(info.get("has_audio"))
    return {"stats": st, "shake": shake, "suggested_style": auto_style, "style": used,
            "reasons": reasons, "adjustments": notes, "params": p}
