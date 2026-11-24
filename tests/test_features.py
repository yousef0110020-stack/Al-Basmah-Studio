"""Feature test-suite: drives the real API (in-process) on the sample files and checks each
feature with a measurement, not just "no error". Writes test-results/feature_results.json.
Usage:  python tests/test_features.py        (run tests/make_samples.py first)"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["STUDIO_DATA_DIR"] = tempfile.mkdtemp(prefix="albasmah_test_")
sys.path.insert(0, str(ROOT / "backend"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import config  # noqa: E402
from app.analyze import image_stats, noise_sigma, shake_score  # noqa: E402
from app.main import app  # noqa: E402
from app.photo import auto_geometry  # noqa: E402

S = ROOT / "samples"
OUT = ROOT / "test-results"
OUT.mkdir(exist_ok=True)
c = TestClient(app)
results = []


def check(name, cond, info=""):
    results.append({"test": name, "pass": bool(cond), "info": info})
    print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info else ""), flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def upload(*names, role=None):
    files = [("files", (n, open(S / n, "rb"))) for n in names]
    r = c.post("/api/upload" + (f"?role={role}" if role else ""), files=files)
    r.raise_for_status()
    return {m["name"]: m for m in r.json()}


def wait(job, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = c.get(f"/api/jobs/{job['id']}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.4)
    raise TimeoutError(job["id"])


def out_path(url):
    return config.OUTPUTS / url.replace("/outputs/", "", 1)


def photo(ids, params, **kw):
    j = wait(c.post("/api/photo/process", json={"file_ids": ids, "params": params, **kw}).json())
    assert j["status"] == "done", j.get("error")
    return j


def video(clips, params, preview=False):
    t0 = time.time()
    j = wait(c.post("/api/video/render", json={"clips": clips, "params": params, "preview": preview}).json())
    if j["status"] != "done":
        return j, None, time.time() - t0
    return j, out_path(j["outputs"][0]["url"]), time.time() - t0


def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)],
                       capture_output=True, text=True).stdout
    return json.loads(o)


def frame(p, t, w=None):
    vf = ["-vf", f"scale={w}:-2"] if w else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(p), "-frames:v", "1", *vf, "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True)
    return np.asarray(Image.open(io.BytesIO(r.stdout)).convert("RGB")).astype(np.float32)


def volume(p, af=None):
    args = ["ffmpeg", "-i", str(p)] + (["-af", af + ",volumedetect"] if af else ["-af", "volumedetect"]) + ["-f", "null", "-"]
    e = subprocess.run(args, capture_output=True, text=True).stderr
    mv = [l for l in e.splitlines() if "mean_volume" in l]
    return float(mv[0].split(":")[1].replace("dB", "")) if mv else None


def main():
    t_start = time.time()
    # ------------------------------------------------------------ setup
    logo = upload("logo_placeholder.png", role="logo")["logo_placeholder.png"]
    c.put("/api/settings", json={"logo_id": logo["id"], "company_ar": "البصمة للعقارات", "company_en": "Al Basmah Real Estate",
                                 "phone": "+971 50 123 4567", "website": "albasmah.ae",
                                 "property": {"title_ar": "فيلا فاخرة للبيع", "title_en": "Luxury Villa for Sale", "price": "4500000",
                                              "currency": "AED", "beds": "5", "baths": "6", "area": "6200", "area_unit": "sqft",
                                              "location_ar": "دبي هيلز", "location_en": "Dubai Hills"}})
    P = upload("facade_tilted_12mp.jpg", "interior_dark_noisy.jpg", "coffee_yellow_cast.jpg", "outdoor_rocket.jpg",
               "iphone_photo.heic", "astronaut_16mp.jpg")
    ids = {k: v["id"] for k, v in P.items()}
    orig_hash = {k: sha(config.ORIGINALS / f"{v['id']}{v['ext']}") for k, v in P.items()}
    check("upload: originals stored read-only", all(not os.access(config.ORIGINALS / f"{v['id']}{v['ext']}", os.W_OK) or os.getuid() == 0
                                                     and (os.stat(config.ORIGINALS / f"{v['id']}{v['ext']}").st_mode & 0o222) == 0
                                                     for v in P.values()))
    check("upload: HEIC (iPhone) decoded", P["iphone_photo.heic"].get("width") == 451, f"{P['iphone_photo.heic'].get('width')}x{P['iphone_photo.heic'].get('height')}")
    check("logo excluded from photo list", all(f["id"] != logo["id"] for f in c.get("/api/files?kind=image").json()))

    # ------------------------------------------------------------ AI analysis
    a = c.post("/api/photo/analyze", json={"file_id": ids["facade_tilted_12mp.jpg"]}).json()
    g = a["geometry"]
    check("auto-analysis: tilt detected (truth 2.5°)", abs(g["rotate"] - 2.5) < 0.4, f"rotate={g['rotate']}")
    check("auto-analysis: converging verticals detected (truth 0.06)", abs(g["perspective_v"] - 0.06) < 0.015, f"pv={g['perspective_v']}")
    an = c.post("/api/photo/analyze", json={"file_id": ids["interior_dark_noisy.jpg"]}).json()
    check("auto-analysis: dark photo -> Night style + denoise", an["style"] == "night" and an["params"]["denoise"] > 0,
          f"style={an['style']} denoise={an['params']['denoise']} exposure={an['params']['exposure']}")
    ac = c.post("/api/photo/analyze", json={"file_id": ids["coffee_yellow_cast.jpg"]}).json()
    check("auto-analysis: non-architectural photo not rotated", ac["params"]["rotate"] == 0 and ac["params"]["perspective_v"] == 0,
          f"geometry confident={ac['geometry']['confident']}")
    check("auto-analysis: colour cast -> white balance on", ac["params"]["auto_wb"] is True)

    # ------------------------------------------------------------ geometry correction result
    j = photo([ids["facade_tilted_12mp.jpg"]], a["params"])
    outp = out_path(j["outputs"][0]["url"])
    o = np.asarray(Image.open(outp).convert("RGB"))
    g2 = auto_geometry(cv2.resize(o, (1600, int(o.shape[0] * 1600 / o.shape[1]))).astype(np.float32) / 255)
    check("perspective + straighten corrected", abs(g2["rotate"]) < 0.5 and abs(g2["perspective_v"]) < 0.015,
          f"after: rotate={g2['rotate']} pv={g2['perspective_v']}")

    # ------------------------------------------------------------ light / night
    src = np.asarray(Image.open(S / "interior_dark_noisy.jpg").convert("RGB"))
    j = photo([ids["interior_dark_noisy.jpg"]], an["params"])
    o = np.asarray(Image.open(out_path(j["outputs"][0]["url"])).convert("RGB"))
    check("light enhancement (dark interior brighter)", o.mean() > src.mean() * 2, f"mean {src.mean():.1f} -> {o.mean():.1f}")
    # denoise effect: same params with/without denoise, compare normalised noise
    p0 = dict(an["params"], denoise=0)
    o0 = np.asarray(Image.open(out_path(photo([ids["interior_dark_noisy.jpg"]], p0)["outputs"][0]["url"])).convert("L"))
    n_with, n_without = noise_sigma(np.asarray(Image.fromarray(o).convert("L"))), noise_sigma(o0)
    check("noise reduction", n_with < n_without * 0.7, f"noise {n_without:.2f} -> {n_with:.2f}")

    # ------------------------------------------------------------ colour cast
    # ground truth: the cast sample = clean photo x (1.12, 1.0, 0.72); measure blue/red balance
    clean = np.asarray(Image.open(S / "src" / "coffee.png").convert("RGB")).astype(float)
    castd = np.asarray(Image.open(S / "coffee_yellow_cast.jpg").convert("RGB")).astype(float)
    o = np.asarray(Image.open(out_path(photo([ids["coffee_yellow_cast.jpg"]], ac["params"])["outputs"][0]["url"])).convert("RGB")).astype(float)
    br = lambda x: x[..., 2].mean() / x[..., 0].mean()
    check("colour correction (yellow cast reduced toward true colours)", abs(br(o) - br(clean)) < abs(br(castd) - br(clean)) * 0.6,
          f"B/R true={br(clean):.3f} cast={br(castd):.3f} corrected={br(o):.3f}")

    # ------------------------------------------------------------ styles
    means = {}
    for st in ["natural", "real_estate", "luxury", "cinematic", "night"]:
        sp = c.post("/api/photo/analyze", json={"file_id": ids["outdoor_rocket.jpg"], "style": st}).json()["params"]
        im = np.asarray(Image.open(out_path(photo([ids["outdoor_rocket.jpg"]], sp)["outputs"][0]["url"])).convert("RGB")).astype(np.float32)
        means[st] = im
    diffs = [float(np.abs(means[a_] - means[b_]).mean()) for i, a_ in enumerate(means) for b_ in list(means)[i + 1:]]
    lux_warm = means["luxury"][..., 0].mean() / means["luxury"][..., 2].mean() > means["natural"][..., 0].mean() / means["natural"][..., 2].mean()
    check("5 styles produce distinct looks", min(diffs) > 2.0, f"min mean abs diff={min(diffs):.1f}")
    check("Luxury style warmer than Natural", lux_warm)

    # ------------------------------------------------------------ object removal
    h, w = 3024, 4032
    m = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(m).rectangle((int(w * 0.66), int(h * 0.80), int(w * 0.78), int(h * 0.93)), fill=(255, 0, 0, 200))
    buf = io.BytesIO(); m.save(buf, "PNG")
    import base64
    mask = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    o = np.asarray(Image.open(out_path(photo([ids["facade_tilted_12mp.jpg"]], {}, masks={ids["facade_tilted_12mp.jpg"]: mask})["outputs"][0]["url"])).convert("RGB")).astype(int)
    srcf = np.asarray(Image.open(S / "facade_tilted_12mp.jpg").convert("RGB")).astype(int)
    reg = (slice(int(h * 0.80), int(h * 0.93)), slice(int(w * 0.66), int(w * 0.78)))
    red = lambda a_: float(((a_[..., 0] > 150) & (a_[..., 1] < 90) & (a_[..., 2] < 90))[reg].mean())
    check("object removal (inpaint red sign)", red(o) < 0.02 and red(srcf) > 0.05, f"red pixels {red(srcf):.3f} -> {red(o):.3f}")

    # ------------------------------------------------------------ logo / watermark / property card
    base = np.asarray(Image.open(out_path(photo([ids["outdoor_rocket.jpg"]], {})["outputs"][0]["url"])).convert("RGB")).astype(int)
    wl = np.asarray(Image.open(out_path(photo([ids["outdoor_rocket.jpg"]], {"logo": True, "logo_position": "bottom-right"})["outputs"][0]["url"])).convert("RGB")).astype(int)
    hh, ww = base.shape[:2]
    br = np.abs(wl - base)[int(hh * 0.75):, int(ww * 0.75):].mean()
    tl = np.abs(wl - base)[:int(hh * 0.25), :int(ww * 0.25)].mean()
    check("logo placed bottom-right only", br > 1 and tl < 0.5, f"diff br={br:.1f} tl={tl:.2f}")
    wm = np.asarray(Image.open(out_path(photo([ids["outdoor_rocket.jpg"]], {"watermark_text": "البصمة"})["outputs"][0]["url"])).convert("RGB")).astype(int)
    check("text watermark (Arabic)", np.abs(wm - base)[int(hh * .35):int(hh * .65), int(ww * .3):int(ww * .7)].mean() > 1.0)
    j = photo([ids["outdoor_rocket.jpg"]], {"property_card": True, "format": "story", "fit": "pad_blur", "card_lang": "ar"})
    o = Image.open(out_path(j["outputs"][0]["url"]))
    check("property card on Story 1080x1920", o.size == (1080, 1920))

    # ------------------------------------------------------------ formats
    exp = {"instagram_post": (1080, 1350), "square": (1080, 1080), "story": (1080, 1920), "landscape": (1920, 1080),
           "landscape_4k": (3840, 2160)}
    sizes = {}
    for f_, sz in exp.items():
        jj = photo([ids["facade_tilted_12mp.jpg"]], {"format": f_, "fit": "crop"})
        sizes[f_] = Image.open(out_path(jj["outputs"][0]["url"])).size
    jj = photo([ids["facade_tilted_12mp.jpg"]], {"format": "web"}); sizes["web"] = Image.open(out_path(jj["outputs"][0]["url"])).size
    jj = photo([ids["facade_tilted_12mp.jpg"]], {"format": "whatsapp"}); sizes["whatsapp"] = Image.open(out_path(jj["outputs"][0]["url"])).size
    check("photo export sizes", all(sizes[k] == v for k, v in exp.items()) and max(sizes["web"]) == 2048 and max(sizes["whatsapp"]) == 1600,
          json.dumps(sizes))
    jj = photo([ids["coffee_yellow_cast.jpg"]], {}, output="png")
    check("PNG export", jj["outputs"][0]["name"].endswith(".png"))

    # ------------------------------------------------------------ batch
    t0 = time.time()
    jb = photo(list(ids.values()), {"logo": True, "format": "web"}, auto_each=True)
    z = [o_ for o_ in jb["outputs"] if o_["kind"] == "zip"][0]
    names = zipfile.ZipFile(out_path(z["url"])).namelist()
    check("batch: 6 photos auto-analysed + ZIP", len(names) == 6, f"{len(names)} files in zip, {time.time() - t0:.1f}s")

    # ------------------------------------------------------------ originals untouched
    check("originals unchanged after all photo jobs",
          all(sha(config.ORIGINALS / f"{v['id']}{v['ext']}") == orig_hash[k] for k, v in P.items()))

    # ============================================================ VIDEO
    V = upload("shaky_1080p.mp4", "portrait_iphone.mov", "clip_4k.mp4", "iphone_hdr_hlg.mov", "music_test.mp3")
    vid = {k: v["id"] for k, v in V.items()}
    vhash = {k: sha(config.ORIGINALS / f"{v['id']}{v['ext']}") for k, v in V.items()}
    va = c.post("/api/video/analyze", json={"file_id": vid["shaky_1080p.mp4"]}).json()
    vb = c.post("/api/video/analyze", json={"file_id": vid["portrait_iphone.mov"]}).json()
    check("video analysis: shake detected only on shaky clip", va["params"]["stabilize"] and not vb["params"]["stabilize"],
          f"shake {va['shake']} vs {vb['shake']}")

    # trim
    j, p, dt = video([{"file_id": vid["shaky_1080p.mp4"], "start": 1, "end": 4}], {"transition": "none"})
    d = float(probe(p)["format"]["duration"])
    check("trim (1s..4s -> 3s)", abs(d - 3) < 0.1, f"{d:.2f}s, {dt:.0f}s render")
    # merge + transition
    j, p, dt = video([{"file_id": vid["shaky_1080p.mp4"], "start": 0, "end": 3}, {"file_id": vid["portrait_iphone.mov"], "start": 0, "end": 3}],
                     {"transition": "fade", "transition_duration": 0.8, "fit": "pad_blur"})
    d = float(probe(p)["format"]["duration"])
    check("merge 2 clips + fade transition (3+3-0.8)", abs(d - 5.2) < 0.1, f"{d:.2f}s")
    mid = frame(p, 2.6, 320)
    check("transition frame is a blend", mid.std() > 5)

    # stabilisation
    _, p_on, dt_on = video([{"file_id": vid["shaky_1080p.mp4"]}], {"stabilize": True, "transition": "none"})
    _, p_off, _ = video([{"file_id": vid["shaky_1080p.mp4"]}], {"stabilize": False, "transition": "none"})
    s_on, s_off = shake_score(str(p_on)), shake_score(str(p_off))
    check("stabilisation reduces shake", s_on < s_off * 0.5, f"jitter {s_off} -> {s_on} px ({dt_on:.0f}s render)")

    # audio denoise: energy of noise band (above 2 kHz) relative to the 220 Hz tone
    _, p_dn, _ = video([{"file_id": vid["shaky_1080p.mp4"]}], {"denoise_audio": True, "transition": "none"})
    hi_off = volume(p_off, "highpass=f=2000,highpass=f=2000") - volume(p_off, "lowpass=f=300,lowpass=f=300")
    hi_on = volume(p_dn, "highpass=f=2000,highpass=f=2000") - volume(p_dn, "lowpass=f=300,lowpass=f=300")
    check("audio noise reduction (noise vs tone)", hi_on < hi_off - 6, f"noise-to-tone {hi_off:.1f} dB -> {hi_on:.1f} dB")

    # music on silent clip
    _, p_m, _ = video([{"file_id": vid["portrait_iphone.mov"]}], {"music_id": vid["music_test.mp3"], "music_volume": 0.5, "preset": "reels"})
    _, p_s, _ = video([{"file_id": vid["portrait_iphone.mov"]}], {"preset": "reels"})
    vm, vs_ = volume(p_m), volume(p_s)
    check("background music added", vm > -40 and (vs_ is None or vs_ < -80), f"mean volume {vs_} -> {vm} dB")

    # colour grading
    _, p_nat, _ = video([{"file_id": vid["shaky_1080p.mp4"], "start": 0, "end": 2}], {**c.post("/api/video/analyze", json={"file_id": vid["shaky_1080p.mp4"], "style": "natural"}).json()["params"], "stabilize": False})
    _, p_lux, _ = video([{"file_id": vid["shaky_1080p.mp4"], "start": 0, "end": 2}], {"contrast": 1.12, "warmth": 0.8, "vignette": 0.5})
    fn, fl = frame(p_nat, 1), frame(p_lux, 1)
    check("colour grading (warm/vignette)", fl[..., 0].mean() / fl[..., 2].mean() > fn[..., 0].mean() / fn[..., 2].mean()
          and fl[:40, :40].mean() < fn[:40, :40].mean(), "R/B ratio up, corners darker")

    # titles AR/EN + property card + end card
    texts = [{"text": "فيلا فاخرة في دبي", "start": 0.3, "end": 2.5, "position": "top", "color": "gold"},
             {"text": "Luxury Villa Dubai", "start": 0.3, "end": 2.5, "position": "bottom", "color": "white", "box": False}]
    _, p_t, _ = video([{"file_id": vid["shaky_1080p.mp4"], "start": 0, "end": 3}], {"texts": texts, "property_card": True, "card_start": 0.5,
                                                                                   "end_card": True, "logo": True})
    _, p_n, _ = video([{"file_id": vid["shaky_1080p.mp4"], "start": 0, "end": 3}], {})
    ft, fn2 = frame(p_t, 1.5), frame(p_n, 1.5)
    top = np.abs(ft - fn2)[60:200, 600:1320].mean()
    card = np.abs(ft - fn2)[800:, :].mean()
    d = float(probe(p_t)["format"]["duration"])
    check("Arabic/English titles rendered", top > 5, f"top region diff={top:.1f}")
    check("property card overlay on video", card > 10, f"bottom region diff={card:.1f}")
    check("end card appended (3s + 4s - 0.8s)", abs(d - 6.2) < 0.15, f"{d:.2f}s")
    Image.fromarray(ft.astype(np.uint8)).save(OUT / "video_frame_titles_card.jpg", quality=88)
    Image.fromarray(frame(p_t, 5.5).astype(np.uint8)).save(OUT / "video_frame_endcard.jpg", quality=88)

    # export presets
    pres = {"landscape_1080": (1920, 1080), "landscape_4k": (3840, 2160), "reels": (1080, 1920), "tiktok": (1080, 1920),
            "square": (1080, 1080), "whatsapp": (1280, 720), "whatsapp_vertical": (720, 1280)}
    info = {}
    for name, (W, H) in pres.items():
        src = vid["clip_4k.mp4"] if name == "landscape_4k" else vid["shaky_1080p.mp4"]
        j, p, dt = video([{"file_id": src, "start": 0, "end": 4}], {"preset": name})
        pr = probe(p)
        vs0 = [s_ for s_ in pr["streams"] if s_["codec_type"] == "video"][0]
        as0 = [s_ for s_ in pr["streams"] if s_["codec_type"] == "audio"]
        head = p.read_bytes()[:4096]
        info[name] = {"size": f"{vs0['width']}x{vs0['height']}", "codec": vs0["codec_name"], "pix": vs0["pix_fmt"],
                      "audio": as0[0]["codec_name"] if as0 else None, "kbps": round(int(pr["format"]["bit_rate"]) / 1000),
                      "faststart": head.find(b"moov") != -1 and head.find(b"moov") < max(head.find(b"mdat"), 4096), "render_s": round(dt)}
        check(f"export preset {name}", vs0["width"] == W and vs0["height"] == H and vs0["codec_name"] == "h264"
              and vs0["pix_fmt"] == "yuv420p" and info[name]["audio"] == "aac", json.dumps(info[name]))
    check("WhatsApp bitrate capped", info["whatsapp"]["kbps"] < 3200, f"{info['whatsapp']['kbps']} kbps")
    check("MP4 faststart (web/phone playback)", all(v["faststart"] for v in info.values()))

    # HDR (simulated iPhone HLG) -> SDR
    j, p, _ = video([{"file_id": vid["iphone_hdr_hlg.mov"]}], {})
    ok = p is not None and probe(p)["streams"][0]["pix_fmt"] == "yuv420p"
    check("HDR (HLG 10-bit HEVC, simulated) -> SDR H.264", ok, j.get("error") or "")

    check("video originals unchanged", all(sha(config.ORIGINALS / f"{v['id']}{v['ext']}") == vhash[k] for k, v in V.items()))

    total = time.time() - t_start
    passed = sum(r["pass"] for r in results)
    print(f"\n{passed}/{len(results)} passed in {total:.0f}s")
    (OUT / "feature_results.json").write_text(json.dumps({"passed": passed, "total": len(results), "seconds": round(total),
                                                           "results": results}, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
