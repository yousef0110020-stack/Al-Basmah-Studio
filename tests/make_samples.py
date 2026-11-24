"""Builds test inputs in samples/: real photographs (from scikit-image's bundled data),
a synthetic 12MP building facade with known tilt + converging verticals, degraded variants
(dark/noisy, colour cast), HEIC, a placeholder logo, test videos (shaky, portrait, 4K, HDR)
and a synthetic music track. Usage: python tests/make_samples.py"""
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "samples"
SRC = S / "src"
FONT = str(ROOT / "assets/fonts/Cairo-700.ttf")
rng = np.random.default_rng(7)


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def facade(w=4032, h=3024):
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(h):  # sky gradient
        t = y / h
        img[y] = (int(120 + 80 * t), int(170 + 50 * t), int(235 - 10 * t))
    bx0, bx1, by0 = int(w * 0.12), int(w * 0.88), int(h * 0.12)
    cv2.rectangle(img, (bx0, by0), (bx1, h), (225, 215, 195), -1)
    for gx in range(bx0 + 80, bx1 - 200, 260):
        for gy in range(by0 + 80, int(h * 0.82), 300):
            cv2.rectangle(img, (gx, gy), (gx + 170, gy + 210), (60, 80, 100), -1)
            cv2.rectangle(img, (gx, gy), (gx + 170, gy + 210), (180, 150, 90), 10)
    cv2.rectangle(img, (0, int(h * 0.9)), (w, h), (90, 90, 85), -1)
    cv2.rectangle(img, (int(w * 0.45), int(h * 0.72)), (int(w * 0.55), int(h * 0.9)), (110, 70, 40), -1)
    # small unwanted object (sign) to test object removal
    cv2.rectangle(img, (int(w * 0.70), int(h * 0.84)), (int(w * 0.74), int(h * 0.9)), (220, 30, 30), -1)
    return img


def make_photos():
    f = facade()
    h, w = f.shape[:2]
    d = 0.06 * w  # converging verticals (camera tilted up): bottom wider than top in the photo
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[d, 0], [w - d, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(src, dst)
    f = cv2.warpPerspective(f, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    R = cv2.getRotationMatrix2D((w / 2, h / 2), -2.5, 1.0)
    f = cv2.warpAffine(f, R, (w, h), borderMode=cv2.BORDER_REPLICATE)
    f = np.clip(f.astype(np.float32) * [1.0, 0.93, 0.8] * 0.75 + rng.normal(0, 4, f.shape), 0, 255).astype(np.uint8)
    Image.fromarray(f).save(S / "facade_tilted_12mp.jpg", quality=92)

    moto = np.asarray(Image.open(SRC / "motorcycle_left.png").convert("RGB")).astype(np.float32)
    dark = np.clip(moto * 0.22 + rng.normal(0, 7, moto.shape), 0, 255).astype(np.uint8)
    Image.fromarray(dark).save(S / "interior_dark_noisy.jpg", quality=90)
    cast = np.clip(np.asarray(Image.open(SRC / "coffee.png").convert("RGB")).astype(np.float32) * [1.12, 1.0, 0.72], 0, 255)
    Image.fromarray(cast.astype(np.uint8)).save(S / "coffee_yellow_cast.jpg", quality=92)
    Image.open(SRC / "rocket.jpg").save(S / "outdoor_rocket.jpg", quality=95)
    big = Image.open(SRC / "astronaut.png").convert("RGB").resize((4000, 4000), Image.LANCZOS)
    big.save(S / "astronaut_16mp.jpg", quality=92)
    import pillow_heif
    pillow_heif.register_heif_opener()
    Image.open(SRC / "chelsea.png").convert("RGB").save(S / "iphone_photo.heic", quality=90)


def make_logo():
    W, H = 1500, 420
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gold = (212, 175, 55, 255)
    d.rounded_rectangle((10, 10, 400, 410), 40, outline=gold, width=14)
    d.text((205, 205), "ب", font=ImageFont.truetype(FONT, 260), fill=gold, anchor="mm")
    d.text((440, 150), "البصمة للعقارات", font=ImageFont.truetype(FONT, 110), fill=gold, anchor="lm", direction="rtl")
    d.text((440, 310), "AL BASMAH REAL ESTATE", font=ImageFont.truetype(FONT, 62), fill=(255, 255, 255, 255), anchor="lm")
    im.save(S / "logo_placeholder.png")


def make_videos():
    # 1) shaky handheld 1080p walk-through with noisy "room tone" + tone, from a real photo
    ff("-loop", "1", "-i", str(SRC / "motorcycle_left.png"), "-f", "lavfi", "-i",
       "anoisesrc=c=pink:a=0.08:d=8", "-f", "lavfi", "-i", "sine=f=220:d=8",
       "-filter_complex",
       "[0:v]scale=2400:-2,crop=2160:1215:x='120+80*t/8+18*sin(t*23)+11*sin(t*37)':y='60+14*cos(t*29)+9*sin(t*41)',"
       "scale=1920:1080,fps=30,format=yuv420p[v];[1:a][2:a]amix=inputs=2:weights='1 0.5'[a]",
       "-map", "[v]", "-map", "[a]", "-t", "8", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", str(S / "shaky_1080p.mp4"))
    # 2) portrait iPhone-style .mov (no audio track) from the facade photo
    ff("-loop", "1", "-i", str(S / "facade_tilted_12mp.jpg"), "-vf",
       "scale=-2:2400,crop=1080:1920:x='(iw-1080)/2+200*sin(t/3)':y=200,fps=30,format=yuv420p",
       "-t", "6", "-c:v", "libx264", "-crf", "20", str(S / "portrait_iphone.mov"))
    # 3) 4K clip with audio
    ff("-loop", "1", "-i", str(S / "outdoor_rocket.jpg"), "-f", "lavfi", "-i", "sine=f=440:d=5",
       "-vf", "scale=4400:-2,crop=3840:2160:x='t*60':y=(ih-2160)/2,fps=30,format=yuv420p",
       "-t", "5", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac", "-shortest", str(S / "clip_4k.mp4"))
    # 4) iPhone-like HDR (HEVC 10-bit HLG tagged)
    ff("-loop", "1", "-i", str(SRC / "coffee.png"), "-vf", "scale=1920:1080,fps=30,format=yuv420p10le",
       "-t", "4", "-c:v", "libx265", "-x265-params", "log-level=error", "-pix_fmt", "yuv420p10le",
       "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
       "-tag:v", "hvc1", str(S / "iphone_hdr_hlg.mov"))
    # 5) synthetic music bed
    ff("-f", "lavfi", "-i", "sine=f=261.6:d=20", "-f", "lavfi", "-i", "sine=f=329.6:d=20", "-f", "lavfi",
       "-i", "sine=f=392:d=20", "-filter_complex", "amix=inputs=3,volume=2,tremolo=f=2:d=0.4,aecho=0.8:0.6:200:0.3",
       "-c:a", "libmp3lame", "-b:a", "192k", str(S / "music_test.mp3"))


if __name__ == "__main__":
    make_photos()
    make_logo()
    make_videos()
    for p in sorted(S.glob("*.*")):
        print(p.name, p.stat().st_size)
