"""Generates the black & gold app icons (PWA / iPhone home screen)."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "icons"
FONT = str(ROOT / "assets" / "fonts" / "Cairo-700.ttf")
OUT.mkdir(parents=True, exist_ok=True)


def gold_gradient(n):
    y, x = np.mgrid[0:n, 0:n] / n
    t = np.clip((x * 0.55 + y * 0.45), 0, 1)[..., None]
    stops = [(0.0, (250, 232, 150)), (0.45, (222, 184, 70)), (0.75, (178, 136, 40)), (1.0, (236, 204, 110))]
    out = np.zeros((n, n, 3), np.float32)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (t >= a) & (t <= b)
        k = (t - a) / (b - a)
        col = np.array(ca) * (1 - k) + np.array(cb) * k
        out = np.where(m, col, out)
    return Image.fromarray(out.astype(np.uint8), "RGB")


def icon(size=1024, maskable=False, text=True):
    S = size * 4  # supersample
    bg = np.zeros((S, S, 3), np.float32)
    y, x = np.mgrid[0:S, 0:S] / S
    glow = np.clip(1 - np.sqrt((x - 0.5) ** 2 + (y - 0.42) ** 2) / 0.75, 0, 1) ** 2
    bg += 10 + glow[..., None] * np.array([46, 36, 12])
    im = Image.fromarray(bg.clip(0, 255).astype(np.uint8), "RGB")
    gold = gold_gradient(S)
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    inset = 0.2 if maskable else 0.13
    a, b = int(S * inset), int(S * (1 - inset))
    w = max(4, int(S * 0.018))
    d.rounded_rectangle((a, a, b, b), radius=int(S * 0.09), outline=255, width=w)
    a2, b2 = a + int(S * 0.035), b - int(S * 0.035)
    d.rounded_rectangle((a2, a2, b2, b2), radius=int(S * 0.065), outline=255, width=max(2, w // 3))
    f = ImageFont.truetype(FONT, int(S * (0.36 if maskable else 0.4)))
    cy = S * (0.44 if text and not maskable else 0.5)
    l, t, r, b = d.textbbox((0, 0), "ب", font=f)   # centre the real glyph (incl. its dot)
    d.text((S / 2 - (l + r) / 2, cy - (t + b) / 2), "ب", font=f, fill=255)
    if text and not maskable:
        ft = ImageFont.truetype(FONT, int(S * 0.058))
        d.text((S / 2, S * 0.735), "AL BASMAH", font=ft, fill=255, anchor="mm")
    shadow = Image.new("RGB", (S, S), (0, 0, 0))
    im.paste(shadow, (int(S * 0.006), int(S * 0.008)), mask.filter(ImageFilter.GaussianBlur(S * 0.006)))
    im.paste(gold, (0, 0), mask)
    return im.resize((size, size), Image.LANCZOS)


big = icon(1024)
big.save(OUT / "icon-1024.png")
for s in (512, 192):
    icon(1024).resize((s, s), Image.LANCZOS).save(OUT / f"icon-{s}.png")
icon(1024, maskable=True).resize((512, 512), Image.LANCZOS).save(OUT / "icon-maskable-512.png")
icon(1024).resize((180, 180), Image.LANCZOS).save(OUT / "apple-touch-icon.png")
small = icon(256, text=False)
small.resize((32, 32), Image.LANCZOS).save(OUT / "favicon-32.png")
small.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print(sorted(p.name for p in OUT.iterdir()))
