"""Photo engine: tone/colour, geometry (straighten + vertical perspective), object removal
(OpenCV inpainting on a user-drawn mask), framing for social formats, logo/watermark and
the real-estate info card. Originals are only read, never written."""
import base64
import io
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config
from .imageio import load_image, to_float, to_pil
from .overlay import font, render_property_card
from .styles import PHOTO_DEFAULTS

# ---------------------------------------------------------------- helpers

def luminance(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def fast_blur(x: np.ndarray, sigma_frac: float) -> np.ndarray:
    """Large-radius gaussian blur computed on a downscaled copy (fast on 24MP images)."""
    h, w = x.shape[:2]
    scale = min(1.0, 600.0 / max(h, w))
    small = cv2.resize(x, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    sigma = max(0.8, sigma_frac * max(small.shape[:2]))
    small = cv2.GaussianBlur(small, (0, 0), sigma)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


# ---------------------------------------------------------------- geometry

def detect_verticals(rgb: np.ndarray):
    """Returns (lines, w, h) where each line = (x_mid, lean, length). lean = dx/dy (top minus bottom)."""
    h, w = rgb.shape[:2]
    scale = min(1.0, 1200.0 / max(h, w))
    small = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor((small * 255).astype(np.uint8) if small.dtype != np.uint8 else small, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 50, 150)
    sh, sw = gray.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=40, minLineLength=sh // 16, maxLineGap=6)
    out = []
    if lines is None:
        return out, sw, sh
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4).astype(float):
        if y1 > y2:  # make (x1,y1) the top point
            x1, y1, x2, y2 = x2, y2, x1, y1
        dy = y2 - y1
        if dy < 5:
            continue
        lean = (x1 - x2) / dy
        if abs(lean) > 0.25:
            continue
        out.append(((x1 + x2) / 2.0, lean, math.hypot(x2 - x1, dy)))
    return out, sw, sh


def auto_geometry(rgb: np.ndarray) -> dict:
    """Fits lean(x) = a*(x-cx)/w + b over near-vertical lines.
    b -> rotation, a -> converging verticals (keystone)."""
    lines, w, h = detect_verticals(rgb)
    res = {"rotate": 0.0, "perspective_v": 0.0, "lines": len(lines), "confident": False}
    if len(lines) < 6:
        return res
    L = np.array(lines, dtype=np.float64)
    X = np.stack([(L[:, 0] - w / 2) / w, np.ones(len(L))], 1)
    y, wt = L[:, 1], L[:, 2]
    keep = np.ones(len(L), bool)
    coef = np.zeros(2)
    for _ in range(4):
        if keep.sum() < 6:
            return res
        W = np.sqrt(wt[keep])
        coef, *_ = np.linalg.lstsq(X[keep] * W[:, None], y[keep] * W, rcond=None)
        r = np.abs(y - X @ coef)
        mad = np.median(r[keep]) + 1e-4
        keep = r < max(3 * mad, 0.01)
    a, b = coef
    rot = math.degrees(math.atan(b))
    pv_raw = -a * h / (2 * w)
    pv = float(np.clip(pv_raw, -0.2, 0.2))
    kept_frac = float(wt[keep].sum() / wt.sum())
    rms = float(np.sqrt(np.average((y[keep] - X[keep] @ coef) ** 2, weights=wt[keep])))
    # Only trust the fit when most line length agrees with one model (architecture);
    # photos of objects/people produce scattered lines and are left untouched.
    confident = bool(keep.sum() >= 8 and kept_frac >= 0.5 and rms < 0.02 and abs(rot) < 7.5 and abs(pv_raw) < 0.2)
    res.update(rotate=round(rot, 2) if abs(rot) >= 0.3 else 0.0,
               perspective_v=round(pv, 3) if abs(pv) >= 0.01 else 0.0,
               lines=int(keep.sum()), kept_fraction=round(kept_frac, 2), rms=round(rms, 4),
               confident=confident)
    return res


def rotated_rect_max(w, h, angle):
    if w <= 0 or h <= 0:
        return 0, 0
    longer = w >= h
    side_long, side_short = (w, h) if longer else (h, w)
    sa, ca = abs(math.sin(angle)), abs(math.cos(angle))
    if side_short <= 2.0 * sa * ca * side_long or abs(sa - ca) < 1e-10:
        x = 0.5 * side_short
        wr, hr = (x / sa, x / ca) if longer else (x / ca, x / sa)
    else:
        cos2a = ca * ca - sa * sa
        wr, hr = (w * ca - h * sa) / cos2a, (h * ca - w * sa) / cos2a
    return wr, hr


def apply_geometry(a: np.ndarray, rotate: float, pv: float) -> np.ndarray:
    h, w = a.shape[:2]
    if abs(pv) >= 0.003:
        d = abs(pv) * w
        if pv > 0:   # verticals converge towards the top -> widen the top
            src = np.float32([[d, 0], [w - d, 0], [w, h], [0, h]])
        else:        # verticals converge towards the bottom -> widen the bottom
            src = np.float32([[0, 0], [w, 0], [w - d, h], [d, h]])
        dst = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        M = cv2.getPerspectiveTransform(src, dst)
        a = cv2.warpPerspective(a, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if abs(rotate) >= 0.05:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rotate, 1.0)
        a = cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        wr, hr = rotated_rect_max(w, h, math.radians(rotate))
        wr, hr = int(wr) - 2, int(hr) - 2
        x0, y0 = (w - wr) // 2, (h - hr) // 2
        a = a[y0:y0 + hr, x0:x0 + wr]
    return a


# ---------------------------------------------------------------- object removal

def decode_mask(data_url: str, size) -> np.ndarray | None:
    if not data_url:
        return None
    raw = base64.b64decode(data_url.split(",", 1)[-1])
    m = Image.open(io.BytesIO(raw)).convert("RGBA")
    m = m.resize(size, Image.NEAREST)
    arr = np.asarray(m)
    mask = ((arr[..., 3] > 10) & (arr[..., :3].max(axis=2) > 10)).astype(np.uint8) * 255
    if mask.max() == 0:
        return None
    k = max(3, int(min(size) * 0.004)) | 1
    return cv2.dilate(mask, np.ones((k, k), np.uint8))


def inpaint(rgb8: np.ndarray, mask: np.ndarray) -> np.ndarray:
    radius = max(3, int(min(rgb8.shape[:2]) * 0.006))
    return cv2.inpaint(rgb8, mask, radius, cv2.INPAINT_TELEA)


# ---------------------------------------------------------------- tone & colour

def denoise8(rgb8: np.ndarray, amount: float) -> np.ndarray:
    hval = 2 + 8 * amount
    if rgb8.shape[0] * rgb8.shape[1] > 16_000_000:
        return cv2.bilateralFilter(rgb8, 7, 20 + 40 * amount, 5)
    return cv2.fastNlMeansDenoisingColored(rgb8, None, hval, hval, 7, 21)


def apply_tone(a: np.ndarray, p: dict) -> np.ndarray:
    eps = 1e-5
    if p.get("auto_wb"):
        lab = cv2.cvtColor(a, cv2.COLOR_RGB2Lab)
        Lc = lab[..., 0]
        chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
        mid = (Lc > 15) & (Lc < 92) & (chroma < 25)   # near-neutral surfaces only
        if mid.sum() > 100:
            for c in (1, 2):
                shift = float(np.mean(lab[..., c][mid]))
                lab[..., c] -= 0.6 * np.clip(shift, -20, 20)  # partial: keep natural warmth
            a = np.clip(cv2.cvtColor(lab, cv2.COLOR_Lab2RGB), 0, 1)
    if p.get("auto_levels"):
        L = luminance(a)
        lo, hi = np.percentile(L[::4, ::4], [0.5, 99.5])
        lo, hi = min(lo, 0.08), max(hi, 0.85)
        a = np.clip((a - lo) / max(hi - lo, 0.1), 0, None)
    ev = float(p.get("exposure", 0))
    if ev:
        a = a * (2.0 ** ev)
    # highlight shoulder so exposure lifts never hard-clip windows/skies
    t = 0.8
    over = a > t
    if over.any():
        a = np.where(over, t + (1 - t) * (1 - np.exp(-(a - t) / (1 - t))), a)

    L = luminance(a)
    Lb = fast_blur(L, 0.02)
    newL = L.copy()
    s = float(p.get("shadows", 0))
    if s:
        m = 1 - smoothstep(0.0, 0.55, Lb)
        target = np.sqrt(np.clip(newL, 0, 1)) if s > 0 else newL ** 1.6
        newL = newL + abs(s) * 0.45 * m * (target - newL)
    hl = float(p.get("highlights", 0))
    if hl:
        m = smoothstep(0.45, 1.0, Lb)
        if hl < 0:
            newL = newL * (1 + hl * 0.3 * m)
        else:
            newL = newL + hl * 0.35 * m * newL * (1 - np.clip(newL, 0, 1))
    c = float(p.get("contrast", 0))
    if c:
        x = np.clip(newL, 0, 1)
        newL = newL + c * (x * x * (3 - 2 * x) - x) * 1.2
    cl = float(p.get("clarity", 0))
    if cl:
        detail = newL - fast_blur(newL, 0.012)
        newL = newL + cl * 0.8 * detail
    ratio = np.clip((np.clip(newL, 0, None) + eps) / (L + eps), 0, 4)
    a = a * ratio[..., None]

    sat, vib = float(p.get("saturation", 0)), float(p.get("vibrance", 0))
    if sat or vib:
        gray = luminance(a)[..., None]
        chroma = a - gray
        cur = (a.max(axis=2) - a.min(axis=2))[..., None]
        factor = (1 + sat) * (1 + vib * np.clip(1 - cur * 2, 0, 1))
        a = gray + chroma * factor
    w, tn = float(p.get("warmth", 0)), float(p.get("tint", 0))
    if w or tn:
        a = a * np.array([1 + 0.08 * w, 1 - 0.06 * tn, 1 - 0.08 * w], np.float32)
    to, gd = float(p.get("teal_orange", 0)), float(p.get("golden", 0))
    if to or gd:
        Ln = np.clip(luminance(a), 0, 1)[..., None]
        ws, wh = (1 - Ln) ** 2, Ln ** 2
        a = a + to * (ws * np.array([-0.04, 0.01, 0.05], np.float32) + wh * np.array([0.05, 0.015, -0.04], np.float32))
        a = a + gd * wh * np.array([0.045, 0.025, -0.035], np.float32)
    v = float(p.get("vignette", 0))
    if v:
        h, wd = a.shape[:2]
        yy, xx = np.ogrid[:h, :wd]
        r = ((xx - wd / 2) / (wd / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
        a = a * (1 - v * 0.4 * smoothstep(0.35, 2.0, r))[..., None].astype(np.float32)
    return np.clip(a, 0, 1).astype(np.float32)


def sharpen(a: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return a
    sigma = max(0.8, min(a.shape[:2]) / 1600.0)
    blur = cv2.GaussianBlur(a, (0, 0), sigma)
    return np.clip(a + amount * 1.3 * (a - blur), 0, 1)


# ---------------------------------------------------------------- framing / branding

FORMATS = {
    "original": None,
    "instagram_post": (1080, 1350),
    "square": (1080, 1080),
    "story": (1080, 1920),
    "landscape": (1920, 1080),
    "landscape_4k": (3840, 2160),
    "web": 2048,          # long edge
    "whatsapp": 1600,     # long edge, lighter JPEG
}


def frame_image(im: Image.Image, fmt: str, fit: str) -> Image.Image:
    target = FORMATS.get(fmt)
    if target is None:
        return im
    if isinstance(target, int):
        im = im.copy()
        im.thumbnail((target, target), Image.LANCZOS)
        return im
    W, H = target
    if fit == "crop":
        s = max(W / im.width, H / im.height)
        r = im.resize((max(W, round(im.width * s)), max(H, round(im.height * s))), Image.LANCZOS)
        x, y = (r.width - W) // 2, (r.height - H) // 2
        return r.crop((x, y, x + W, y + H))
    # pad: keep the whole property visible
    s = min(W / im.width, H / im.height)
    fg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    if fit == "pad_black":
        bg = Image.new("RGB", (W, H), config.BLACK)
    else:
        sb = max(W / im.width, H / im.height)
        bg = im.resize((max(1, round(im.width * sb / 8)), max(1, round(im.height * sb / 8))), Image.BILINEAR)
        bg = bg.filter(ImageFilter.GaussianBlur(6)).resize((max(W, round(im.width * sb)), max(H, round(im.height * sb))), Image.BILINEAR)
        x, y = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((x, y, x + W, y + H))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.35)
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    return bg


def place_logo(im: Image.Image, logo: Image.Image, position="bottom-right", size=0.14, opacity=0.9,
               avoid_bottom=0) -> Image.Image:
    im = im.convert("RGBA")
    lw = max(16, int(im.width * size))
    lg = logo.convert("RGBA")
    lg = lg.resize((lw, max(1, int(lg.height * lw / lg.width))), Image.LANCZOS)
    if opacity < 1:
        alpha = lg.getchannel("A").point(lambda v: int(v * opacity))
        lg.putalpha(alpha)
    m = int(min(im.size) * 0.035)
    x = m if "left" in position else (im.width - lg.width - m if "right" in position else (im.width - lg.width) // 2)
    if position.startswith("top"):
        y = m
    elif position.startswith("bottom"):
        y = im.height - lg.height - m - avoid_bottom
    else:
        y = (im.height - lg.height) // 2
    im.alpha_composite(lg, (x, max(0, y)))
    return im


def text_watermark(im: Image.Image, text: str, opacity=0.18) -> Image.Image:
    im = im.convert("RGBA")
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    f = font(int(im.width * 0.06), bold=True)
    d = ImageDraw.Draw(layer)
    direction = "rtl" if any("؀" <= ch <= "ۿ" for ch in text) else None
    d.text((im.width / 2, im.height / 2), text, font=f, fill=(255, 255, 255, int(255 * opacity)),
           anchor="mm", direction=direction)
    im.alpha_composite(layer)
    return im


# ---------------------------------------------------------------- pipeline

def process(path: str, params: dict, brand: dict, logo: Image.Image | None, max_size: int | None = None,
            progress=lambda f: None) -> Image.Image:
    p = dict(PHOTO_DEFAULTS)
    p.update(params or {})
    im = load_image(path)
    if max_size:
        im.thumbnail((max_size, max_size), Image.LANCZOS)
    rgb8 = np.asarray(im.convert("RGB")).copy()
    progress(0.1)
    mask = decode_mask(p.get("inpaint_mask"), (rgb8.shape[1], rgb8.shape[0]))
    if mask is not None:
        rgb8 = inpaint(rgb8, mask)
    if float(p.get("denoise", 0)) > 0:
        rgb8 = denoise8(rgb8, float(p["denoise"]))
    progress(0.35)
    a = rgb8.astype(np.float32) / 255.0
    a = apply_geometry(a, float(p.get("rotate", 0)), float(p.get("perspective_v", 0)))
    progress(0.5)
    a = apply_tone(a, p)
    a = sharpen(a, float(p.get("sharpen", 0)))
    progress(0.8)
    out = to_pil(a)
    out = frame_image(out, p.get("format", "original"), p.get("fit", "pad_blur"))
    card_h = 0
    if p.get("property_card"):
        card = render_property_card(out.width, out.height, brand, logo, lang=p.get("card_lang", "ar"))
        out = out.convert("RGBA")
        out.alpha_composite(card)
        card_h = int(out.height * 0.3)
    if p.get("watermark_text"):
        out = text_watermark(out, p["watermark_text"], float(p.get("watermark_opacity", 0.18)))
    if p.get("logo") and logo is not None and not p.get("property_card"):
        out = place_logo(out, logo, p.get("logo_position", "bottom-right"), float(p.get("logo_size", 0.14)),
                         float(p.get("logo_opacity", 0.9)))
    progress(0.95)
    return out.convert("RGB")
