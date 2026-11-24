"""Image loading helpers (EXIF orientation, HEIC, float conversion)."""
import numpy as np
from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pass

Image.MAX_IMAGE_PIXELS = 200_000_000


def load_image(path: str) -> Image.Image:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
    return im


def to_float(im: Image.Image) -> np.ndarray:
    """PIL RGB -> float32 HxWx3 in 0..1"""
    a = np.asarray(im.convert("RGB"))
    if a.dtype == np.uint16:
        return a.astype(np.float32) / 65535.0
    return a.astype(np.float32) / 255.0


def to_pil(a: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(a, 0, 1) * 255.0 + 0.5).astype(np.uint8), "RGB")
