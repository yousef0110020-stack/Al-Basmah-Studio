"""Video engine built on FFmpeg: trim, order, stabilise (vid.stab), colour grade, denoise,
audio clean-up, music, transitions (xfade), Arabic/English titles, real-estate card,
logo, end card and export presets (1080p, 4K, Reels/TikTok, WhatsApp)."""
import json
import os
import subprocess
from pathlib import Path

from PIL import Image

from . import config
from .overlay import render_end_card, render_property_card, render_text_layer
from .storage import original_path, get_meta, video_info
from .styles import VIDEO_DEFAULTS

PRESETS = {
    # name: (W, H, crf, x264 preset, maxrate)
    "landscape_1080": (1920, 1080, 19, "medium", None),
    "landscape_4k": (3840, 2160, 20, "faster", None),
    "reels": (1080, 1920, 19, "medium", None),
    "tiktok": (1080, 1920, 19, "medium", None),
    "square": (1080, 1080, 19, "medium", None),
    "whatsapp": (1280, 720, 23, "medium", "2500k"),
    "whatsapp_vertical": (720, 1280, 23, "medium", "2500k"),
}
TRANSITIONS = {"none", "fade", "fadeblack", "dissolve", "slideleft", "slideright", "wipeleft",
               "circleopen", "smoothleft", "zoomin"}
FPS = 30


def even(x):
    return max(2, int(round(x / 2)) * 2)


class Cancelled(Exception):
    pass


def run_ffmpeg(args: list, duration: float, cb, log_path: Path):
    """Runs ffmpeg, reporting progress fraction 0..1 via cb. Raises with stderr tail on failure."""
    cmd = [config.FFMPEG, "-y", "-hide_banner", "-nostats", "-progress", "pipe:1"] + args
    with open(log_path, "a") as log:
        log.write("\n$ " + " ".join(cmd) + "\n")
        log.flush()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log, text=True)
        for line in p.stdout:
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    us = int(line.split("=")[1])
                    cb(min(1.0, us / 1e6 / max(duration, 0.01)))
                except ValueError:
                    pass
        p.wait()
    if p.returncode != 0:
        tail = log_path.read_text()[-1500:]
        raise RuntimeError(f"ffmpeg failed: {tail}")
    cb(1.0)


def probe_duration(path) -> float:
    out = subprocess.run([config.FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def grade_filters(p: dict) -> list:
    f = []
    d = float(p.get("denoise", 0))
    if d > 0:
        f.append(f"hqdn3d={1.5 + 4 * d:.2f}:{1.5 + 3 * d:.2f}:{3 + 6 * d:.2f}:{3 + 4 * d:.2f}")
    f.append("eq=brightness={:.3f}:contrast={:.3f}:saturation={:.3f}:gamma={:.3f}".format(
        float(p.get("brightness", 0)), float(p.get("contrast", 1)), float(p.get("saturation", 1)),
        float(p.get("gamma", 1))))
    w, t = float(p.get("warmth", 0)), float(p.get("teal_orange", 0))
    if w or t:
        cb = {"rs": -0.06 * t, "bs": 0.08 * t + -0.02 * w, "rm": 0.06 * w, "bm": -0.06 * w,
              "rh": 0.04 * w + 0.07 * t, "bh": -0.04 * w - 0.06 * t}
        f.append("colorbalance=" + ":".join(f"{k}={v:.3f}" for k, v in cb.items()))
    v = float(p.get("vignette", 0))
    if v > 0:
        f.append(f"vignette=angle={0.25 + 0.45 * v:.3f}")
    s = float(p.get("sharpen", 0))
    if s > 0:
        f.append(f"unsharp=5:5:{0.3 + 1.0 * s:.2f}:5:5:0")
    return f


def hdr_filter(info: dict) -> str | None:
    if info.get("color_transfer") in ("arib-std-b67", "smpte2084"):
        return ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    return None


def build_segment(src, info, start, dur, W, H, p, fit, out, work, idx, preview, cb, log):
    sw, sh = info["width"], info["height"]
    s = max(W / sw, H / sh) if fit == "crop" else min(1.0, max(W, H) / max(sw, sh))
    s = min(s, 1.0)
    pw, ph = even(sw * s), even(sh * s)
    pre = [x for x in [hdr_filter(info), f"scale={pw}:{ph}:flags=lanczos"] if x]
    stab = []
    total_units = 2 if p.get("stabilize") else 1
    if p.get("stabilize"):
        trf = work / f"seg{idx}.trf"
        run_ffmpeg(["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src, "-an", "-vf",
                    ",".join(pre + [f"vidstabdetect=shakiness=6:accuracy=12:result={trf}"]), "-f", "null", "-"],
                   dur, lambda f: cb(f / total_units), log)
        stab = [f"vidstabtransform=input={trf}:smoothing=18:optzoom=1:zoomspeed=0.2:interpol=bicubic"]
    chain = ",".join(pre + stab)
    if fit == "crop":
        vf = f"[0:v]{chain},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
    else:
        bw, bh = even(W / 6), even(H / 6)
        bg = ("eq=brightness=-0.08,boxblur=8:2" if fit == "pad_blur" else "drawbox=c=black:t=fill")
        vf = (f"[0:v]{chain},split[a][b];[a]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
              f"{bg},scale={W}:{H}[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    vf += "," + ",".join(grade_filters(p) + [f"fps={FPS}", "setsar=1", "format=yuv420p"]) + "[v]"
    inputs = ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]
    if p.get("keep_audio", True) and info.get("has_audio"):
        af = "[0:a]aresample=48000,aformat=channel_layouts=stereo"
        if p.get("denoise_audio"):
            af += ",highpass=f=80,afftdn=nf=-25:nt=w,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
        af += "[a]"
    else:
        inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        af = "[1:a]anull[a]"
    script = work / f"seg{idx}.filter"
    script.write_text(vf + ";" + af)
    enc = ["-c:v", "libx264", "-crf", "30" if preview else "16", "-preset", "ultrafast" if preview else "veryfast",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    run_ffmpeg(inputs + ["-filter_complex_script", str(script), "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}"]
               + enc + [str(out)], dur, lambda f: cb((total_units - 1 + f) / total_units), log)


def build_still(png, dur, W, H, out, preview, cb, log):
    run_ffmpeg(["-loop", "1", "-framerate", str(FPS), "-t", f"{dur}", "-i", str(png), "-f", "lavfi", "-t", f"{dur}",
                "-i", "anullsrc=r=48000:cl=stereo", "-vf", f"scale={W}:{H},setsar=1,format=yuv420p",
                "-c:v", "libx264", "-crf", "30" if preview else "16", "-preset", "ultrafast" if preview else "veryfast",
                "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], dur, cb, log)


def merge(segments, transition, tdur, out, preview, cb, log, work):
    durs = [probe_duration(s) for s in segments]
    if transition == "none" or len(segments) == 1:
        lst = work / "concat.txt"
        lst.write_text("".join(f"file '{s}'\n" for s in segments))
        run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], sum(durs), cb, log)
        return sum(durs)
    T = max(0.2, min(tdur, min(durs) / 2 - 0.05))
    inputs, vparts, aparts = [], [], []
    for s in segments:
        inputs += ["-i", str(s)]
    off, vprev, aprev = 0.0, "[0:v]", "[0:a]"
    for i in range(1, len(segments)):
        off += durs[i - 1] - T
        vparts.append(f"{vprev}[{i}:v]xfade=transition={transition}:duration={T:.3f}:offset={off:.3f}[v{i}]")
        aparts.append(f"{aprev}[{i}:a]acrossfade=d={T:.3f}[a{i}]")
        vprev, aprev = f"[v{i}]", f"[a{i}]"
    n = len(segments) - 1
    script = work / "merge.filter"
    script.write_text(";".join(vparts + aparts))
    total = sum(durs) - T * n
    run_ffmpeg(inputs + ["-filter_complex_script", str(script), "-map", f"[v{n}]", "-map", f"[a{n}]",
                         "-c:v", "libx264", "-crf", "30" if preview else "16",
                         "-preset", "ultrafast" if preview else "veryfast", "-pix_fmt", "yuv420p",
                         "-c:a", "aac", "-b:a", "192k", str(out)], total, cb, log)
    return total


def render(job, clips: list, params: dict, brand: dict, logo_path: str | None, out_dir: Path, preview=False):
    p = dict(VIDEO_DEFAULTS)
    p.update(params or {})
    W, H, crf, preset, maxrate = PRESETS.get(p.get("preset", "landscape_1080"), PRESETS["landscape_1080"])
    if preview:
        k = 640 / max(W, H)
        W, H = even(W * k), even(H * k)
    fit = p.get("fit", "crop")
    work = config.WORK / job.id
    work.mkdir(parents=True, exist_ok=True)
    log = work / "ffmpeg.log"
    logo = Image.open(logo_path).convert("RGBA") if logo_path and os.path.exists(logo_path) else None

    plan = []
    for c in clips:
        meta = get_meta(c["file_id"])
        src = original_path(c["file_id"])
        info = video_info(src)
        start = max(0.0, float(c.get("start") or 0))
        end = float(c.get("end") or info["duration"])
        end = min(end, info["duration"])
        if end - start < 0.3:
            raise ValueError(f"clip too short: {meta['name']}")
        plan.append((src, info, start, end - start))
    stab_w = 2 if p.get("stabilize") else 1
    weights = [d * stab_w for *_, d in plan]
    total_in = sum(d for *_, d in plan)
    W_seg, W_merge, W_final = sum(weights), total_in * 0.4, total_in * 0.8
    grand = W_seg + W_merge + W_final
    done = [0.0]

    def stage(base, span):
        return lambda f: job.set_progress(5 + 93 * (base + span * f) / grand)

    segments = []
    for i, (src, info, start, dur) in enumerate(plan):
        job.message = f"clip {i + 1}/{len(plan)}"
        seg = work / f"seg{i}.mp4"
        build_segment(src, info, start, dur, W, H, p, fit, seg, work, i, preview, stage(done[0], weights[i]), log)
        done[0] += weights[i]
        segments.append(seg)
    if p.get("end_card"):
        png = work / "endcard.png"
        render_end_card(W, H, brand, logo, p.get("card_lang", "ar")).save(png)
        seg = work / "endcard.mp4"
        build_still(png, float(p.get("end_card_duration", 4)), W, H, seg, preview, lambda f: None, log)
        segments.append(seg)

    job.message = "merging"
    merged = work / "merged.mp4"
    total = merge(segments, p.get("transition", "fade") if p.get("transition") in TRANSITIONS else "fade",
                  float(p.get("transition_duration", 0.8)), merged, preview, stage(done[0], W_merge), log, work)
    done[0] += W_merge
    total = probe_duration(merged)

    job.message = "finishing"
    inputs = ["-i", str(merged)]
    vf = "[0:v]null"
    landscape = W > H
    if p.get("letterbox") and landscape:
        bar = even((H - W / 2.39) / 2)
        vf += f",drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill"
    vf += "[vt]"
    graph, vlast, idx = [vf], "[vt]", 1
    if p.get("property_card"):
        card = work / "card.png"
        render_property_card(W, H, brand, logo, p.get("card_lang", "ar")).save(card)
        cs = float(p.get("card_start", 1.0))
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(card)]
        ce = total - (float(p.get("end_card_duration", 4)) if p.get("end_card") else 0) - 0.1
        graph.append(f"[{idx}:v]format=rgba,fade=t=in:st={cs}:d=0.8:alpha=1,fade=t=out:st={max(cs, ce - 0.6):.2f}:d=0.6:alpha=1[card]")
        graph.append(f"{vlast}[card]overlay=0:0:shortest=1:enable='between(t,{cs},{ce:.2f})'[vc]")
        vlast, idx = "[vc]", idx + 1
    elif p.get("logo") and logo_path:
        lw = even(W * float(p.get("logo_size", 0.14)))
        m = int(min(W, H) * 0.035)
        pos = p.get("logo_position", "top-right")
        x = f"{m}" if "left" in pos else f"W-w-{m}"
        y = f"{m}" if pos.startswith("top") else f"H-h-{m}"
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", logo_path]
        graph.append(f"[{idx}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={float(p.get('logo_opacity', 0.9)):.2f}[lg]")
        graph.append(f"{vlast}[lg]overlay={x}:{y}:shortest=1[vc]")
        vlast, idx = "[vc]", idx + 1
    for i, t in enumerate(p.get("texts") or []):
        txt = (t.get("text") or "").strip()
        if not txt:
            continue
        ts, te = float(t.get("start", 0)), float(t.get("end", 5))
        te = min(te, total)
        if te - ts < 0.3:
            continue
        png = work / f"text{i}.png"
        render_text_layer(W, H, txt, t.get("position", "bottom"), float(t.get("size", 0.06)),
                          t.get("color", "white"), bool(t.get("box", True))).save(png)
        fd = min(0.4, (te - ts) / 3)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(png)]
        graph.append(f"[{idx}:v]format=rgba,fade=t=in:st={ts}:d={fd:.2f}:alpha=1,"
                     f"fade=t=out:st={te - fd:.2f}:d={fd:.2f}:alpha=1[t{i}]")
        graph.append(f"{vlast}[t{i}]overlay=0:0:shortest=1:enable='between(t,{ts},{te})'[vt{i}]")
        vlast, idx = f"[vt{i}]", idx + 1
    alast = "0:a"
    if p.get("music_id"):
        mpath = original_path(p["music_id"])
        vol = float(p.get("music_volume", 0.35))
        inputs += ["-stream_loop", "-1", "-i", mpath]
        fo = max(0.0, total - 2.5)
        graph.append(f"[{idx}:a]atrim=0:{total:.3f},asetpts=N/SR/TB,aresample=48000,aformat=channel_layouts=stereo,"
                     f"volume={vol:.2f},afade=t=in:d=1,afade=t=out:st={fo:.2f}:d=2.5[mus]")
        graph.append(f"[0:a][mus]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[am]")
        alast, idx = "[am]", idx + 1
    script = work / "final.filter"
    script.write_text(";".join(graph))
    name = "preview.mp4" if preview else f"albasmah_{p.get('preset', 'landscape_1080')}.mp4"
    out = out_dir / name
    enc = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart"]
    if preview:
        enc += ["-crf", "30", "-preset", "ultrafast"]
    else:
        enc += ["-crf", str(crf), "-preset", preset]
        if maxrate:
            enc += ["-maxrate", maxrate, "-bufsize", str(int(maxrate[:-1]) * 2) + "k"]
    run_ffmpeg(inputs + ["-filter_complex_script", str(script), "-map", vlast, "-map", alast, "-t", f"{total:.3f}"]
               + enc + [str(out)], total, stage(done[0], W_final), log)
    if not preview:
        for s in work.glob("*.mp4"):
            s.unlink(missing_ok=True)
    return out
