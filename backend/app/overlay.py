"""Black & gold real-estate graphics (info card, end card) rendered with Pillow + raqm
so Arabic is shaped and ordered correctly. Only text/graphics are added on top of the
photo; the property itself is never altered."""
import re
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config

GOLD = (212, 175, 55, 255)
GOLD_LIGHT = (240, 210, 120, 255)
WHITE = (255, 255, 255, 255)
GREY = (205, 205, 205, 255)


@lru_cache(maxsize=64)
def font(size: int, bold=False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(config.FONT_BOLD if bold else config.FONT_REGULAR, max(8, int(size)),
                              layout_engine=ImageFont.Layout.RAQM)


def is_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ" for ch in text or "")


def fmt_number(v) -> str:
    s = str(v or "").strip()
    digits = re.sub(r"[,\s]", "", s)
    if re.fullmatch(r"\d+(\.\d+)?", digits):
        n = float(digits)
        return f"{n:,.0f}" if n == int(n) else f"{n:,.2f}"
    return s


def property_lines(brand: dict, lang: str) -> dict:
    pr = brand.get("property", {}) or {}
    ar = lang == "ar"
    title = pr.get("title_ar" if ar else "title_en") or pr.get("title_en" if ar else "title_ar") or ""
    loc = pr.get("location_ar" if ar else "location_en") or pr.get("location_en" if ar else "location_ar") or ""
    extra = pr.get("extra_ar" if ar else "extra_en") or ""
    specs = []
    if pr.get("beds"):
        specs.append(f"{pr['beds']} غرف نوم" if ar else f"{pr['beds']} Beds")
    if pr.get("baths"):
        specs.append(f"{pr['baths']} حمّامات" if ar else f"{pr['baths']} Baths")
    if pr.get("area"):
        unit = pr.get("area_unit", "sqft")
        u = ("قدم²" if unit == "sqft" else "م²") if ar else ("sq.ft" if unit == "sqft" else "sqm")
        specs.append(f"{fmt_number(pr['area'])} {u}")
    if extra:
        specs.append(extra)
    price = ""
    if pr.get("price"):
        cur = pr.get("currency", "AED")
        curl = {"AED": "درهم", "USD": "دولار", "SAR": "ريال"}.get(cur, cur) if ar else cur
        price = f"{fmt_number(pr['price'])} {curl}" if ar else f"{cur} {fmt_number(pr['price'])}"
    company = brand.get("company_ar" if ar else "company_en") or brand.get("company_en" if ar else "company_ar") or ""
    return {"title": title, "specs": "  |  ".join(specs), "location": loc, "price": price,
            "phone": ("\u2066" + brand["phone"] + "\u2069") if brand.get("phone") else "", "company": company, "website": brand.get("website", ""),
            "ref": pr.get("ref", "")}


def _fit(text, size, bold, max_w):
    f = font(size, bold)
    while size > 10 and f.getlength(text, direction="rtl" if is_arabic(text) else None) > max_w:
        size = int(size * 0.92)
        f = font(size, bold)
    return f


def _draw(d, x, y, text, f, fill, align):
    """align: 'r' or 'l' or 'm'. y is the top of the line box."""
    direction = "rtl" if is_arabic(text) else None
    anchor = {"r": "ra", "l": "la", "m": "ma"}[align]
    d.text((x, y), text, font=f, fill=fill, anchor=anchor, direction=direction)


def render_property_card(W: int, H: int, brand: dict, logo: Image.Image | None, lang="ar") -> Image.Image:
    info = property_lines(brand, lang)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    portrait = H > W * 1.2
    unit = min(W, H) * (0.05 if portrait else 0.04)
    m = int(W * 0.045)
    band_h = int(H * (0.26 if portrait else 0.34))
    # gradient band
    grad = np.clip(np.linspace(0, 1.25, band_h), 0, 1) ** 1.1 * 238
    band = np.zeros((band_h, W, 4), np.uint8)
    band[..., 3] = grad[:, None].astype(np.uint8)
    layer.alpha_composite(Image.fromarray(band, "RGBA"), (0, H - band_h))
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(text_layer)
    rtl = lang == "ar"
    text_w = W * (0.62 if not portrait else 0.9)
    tx = W - m if rtl else m
    al = "r" if rtl else "l"

    rows = []
    if info["title"]:
        rows.append((info["title"], unit * 1.25, True, WHITE))
    if info["specs"]:
        rows.append((info["specs"], unit * 0.72, False, GREY))
    if info["location"]:
        rows.append((info["location"], unit * 0.68, False, GREY))
    if info["price"]:
        rows.append((info["price"], unit * 1.1, True, GOLD))
    fonts = [(_fit(t, s, b, text_w), t, c) for t, s, b, c in rows]
    gap = unit * 0.25
    heights = [f.size * 1.45 for f, _, _ in fonts]
    contact_h = 0
    if portrait:  # contact row goes under the text block
        contact_h = unit * 1.6
    y = H - m - sum(heights) - contact_h
    text_top = y
    # gold accent line above text
    lx0, lx1 = (tx - W * 0.18, tx) if rtl else (tx, tx + W * 0.18)
    d.line([(lx0, y - gap * 1.5), (lx1, y - gap * 1.5)], fill=GOLD, width=max(2, int(unit * 0.08)))
    for (f, t, c), hgt in zip(fonts, heights):
        _draw(d, tx, y, t, f, c, al)
        y += hgt

    # contact block: logo + phone + company
    phone = info["phone"]
    company = info["company"]
    if portrait:
        cy = H - m - contact_h + unit * 0.2
        cx = m if rtl else W - m
        cal = "l" if rtl else "r"
        line = "   ".join(x for x in [phone, company] if x)
        if line:
            _draw(d, cx, cy, line, _fit(line, unit * 0.75, True, W * 0.6), GOLD_LIGHT, cal)
        if logo is not None:
            lh = int(unit * 2.2)
            lg = logo.convert("RGBA")
            lg = lg.resize((max(1, int(lg.width * lh / lg.height)), lh), Image.LANCZOS)
            if lg.width > W * 0.3:
                lg = lg.resize((int(W * 0.3), max(1, int(lg.height * W * 0.3 / lg.width))), Image.LANCZOS)
            lx = W - m - lg.width if rtl else m
            layer.alpha_composite(lg, (lx, int(text_top - gap * 1.5 - unit * 0.5 - lg.height)))
            # logo sits at the top-right of the band (above the title) in portrait
    else:
        cx = m if rtl else W - m
        cal = "l" if rtl else "r"
        bottom = H - m
        yy = bottom
        if company:
            fc = _fit(company, unit * 0.62, False, W * 0.3)
            yy -= fc.size * 1.4
            _draw(d, cx, yy, company, fc, WHITE, cal)
        if phone:
            fp = _fit(phone, unit * 0.85, True, W * 0.3)
            yy -= fp.size * 1.45
            _draw(d, cx, yy, phone, fp, GOLD, cal)
        if logo is not None:
            lh = int(band_h * 0.36)
            lg = logo.convert("RGBA")
            lg = lg.resize((max(1, int(lg.width * lh / lg.height)), lh), Image.LANCZOS)
            if lg.width > W * 0.26:
                lg = lg.resize((int(W * 0.26), max(1, int(lg.height * W * 0.26 / lg.width))), Image.LANCZOS)
            lx = m if rtl else W - m - lg.width
            layer.alpha_composite(lg, (lx, int(yy - lg.height - unit * 0.3)))
    # soft drop shadow under all text for legibility on busy backgrounds
    shadow_a = text_layer.getchannel("A").filter(ImageFilter.GaussianBlur(max(2, unit * 0.12)))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(shadow_a.point(lambda v: int(v * 0.85)))
    layer.alpha_composite(shadow)
    layer.alpha_composite(text_layer)
    return layer


def render_end_card(W: int, H: int, brand: dict, logo: Image.Image | None, lang="ar") -> Image.Image:
    info = property_lines(brand, lang)
    yy, xx = np.ogrid[:H, :W]
    r = np.sqrt(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H * 0.42) / (H * 0.7)) ** 2)
    glow = np.clip(1 - r, 0, 1) ** 2
    bg = np.zeros((H, W, 3), np.float32)
    bg += glow[..., None] * np.array([70, 55, 18], np.float32)
    bg += 8
    im = Image.fromarray(bg.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    unit = min(W, H) * 0.045
    y = H * 0.16
    if logo is not None:
        lh = int(min(H * 0.2, W * 0.35))
        lg = logo.convert("RGBA")
        lg = lg.resize((max(1, int(lg.width * lh / lg.height)), lh), Image.LANCZOS)
        if lg.width > W * 0.6:
            lg = lg.resize((int(W * 0.6), max(1, int(lg.height * W * 0.6 / lg.width))), Image.LANCZOS)
        im.alpha_composite(lg, ((W - lg.width) // 2, int(y)))
        y += lg.height + unit * 0.8
    rows = [(info["company"], unit * 1.0, True, GOLD), ("__line__", 0, False, None),
            (info["title"], unit * 1.15, True, WHITE), (info["specs"], unit * 0.7, False, GREY),
            (info["price"], unit * 1.1, True, GOLD), (info["phone"], unit * 1.0, True, WHITE),
            (info["website"], unit * 0.65, False, GREY)]
    for t, s, b, c in rows:
        if t == "__line__":
            d.line([(W * 0.38, y + unit * 0.2), (W * 0.62, y + unit * 0.2)], fill=GOLD, width=max(2, int(unit * 0.07)))
            y += unit * 0.9
            continue
        if not t:
            continue
        f = _fit(t, s, b, W * 0.86)
        _draw(d, W / 2, y, t, f, c, "m")
        y += f.size * 1.6
    return im.convert("RGB")


def render_text_layer(W: int, H: int, text: str, position="bottom", size=0.06, color="white", box=True) -> Image.Image:
    """Full-frame transparent layer with one Arabic/English title (used for video titles)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fill = {"gold": GOLD, "white": WHITE, "black": (0, 0, 0, 255)}.get(color, WHITE)
    f = _fit(text, min(W, H) * float(size), True, W * 0.88)
    direction = "rtl" if is_arabic(text) else None
    d = ImageDraw.Draw(layer)
    l, t, r, b = d.textbbox((0, 0), text, font=f, anchor="la", direction=direction)
    tw, th = r - l, b - t
    pad = int(f.size * 0.4)
    x = (W - tw) // 2
    y = {"top": int(H * 0.08), "center": (H - th) // 2}.get(position, int(H * 0.88 - th))
    if box:
        d.rounded_rectangle((x - pad, y - pad, x + tw + pad, y + th + pad), radius=pad // 2, fill=(0, 0, 0, 120))
        d.line([(x - pad, y + th + pad), (x + tw + pad, y + th + pad)], fill=GOLD, width=max(2, f.size // 18))
    else:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x - l, y - t), text, font=f, fill=(0, 0, 0, 200), anchor="la", direction=direction)
        layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(f.size * 0.08)))
        d = ImageDraw.Draw(layer)
    d.text((x - l, y - t), text, font=f, fill=fill, anchor="la", direction=direction)
    return layer
