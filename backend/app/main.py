"""Al Basmah AI Media Studio - FastAPI application."""
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

from . import analyze, auth, config, jobs, photo, storage, video
from .imageio import load_image
from .styles import PHOTO_DEFAULTS, STYLES

app = FastAPI(title="Al Basmah AI Media Studio", version="0.1.0")


def _is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "") == "https"


@app.middleware("http")
async def security(request: Request, call_next):
    """Login wall (when STUDIO_PASSWORD is set) + security headers."""
    path = request.url.path
    if auth.enabled() and not auth.is_public(path) and not auth.valid(request.cookies.get(auth.COOKIE)):
        if path.startswith("/api/") or path.startswith("/outputs/"):
            return JSONResponse({"detail": "login required"}, status_code=401)
        return RedirectResponse("/login.html", status_code=303)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["X-Frame-Options"] = "DENY"
    if _is_https(request):
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    if path in ("/", "/index.html", "/sw.js", "/app.js", "/login.html"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


class LoginReq(BaseModel):
    password: str


@app.post("/api/login")
def login(r: LoginReq, request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    if not auth.enabled():
        return {"ok": True, "auth": False}
    if auth.too_many(ip):
        raise HTTPException(429, "too many attempts, try again in 15 minutes")
    if not auth.check_password(r.password):
        auth.record_fail(ip)
        raise HTTPException(401, "wrong password")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(auth.COOKIE, auth.make_token(), max_age=auth.MAX_AGE, httponly=True,
                    secure=_is_https(request), samesite="lax", path="/")
    return resp


@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


@app.get("/api/me")
def me():
    return {"auth": auth.enabled()}


# ------------------------------------------------------------------ files

@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...), role: str | None = None):
    out = []
    for f in files:
        out.append(storage.save_upload(f.file, f.filename or "file", role=role))
    return out


@app.get("/api/files")
def files(kind: str | None = None):
    return storage.list_files(kind)


def _meta_or_404(fid):
    try:
        return storage.get_meta(fid)
    except KeyError:
        raise HTTPException(404, "file not found")


@app.get("/api/files/{fid}/original")
def original(fid: str):
    m = _meta_or_404(fid)
    return FileResponse(storage.original_path(fid), filename=m["name"])


@app.get("/api/files/{fid}/thumb")
def thumb(fid: str):
    _meta_or_404(fid)
    p = config.THUMBS / f"{fid}.jpg"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/files/{fid}/view")
def view(fid: str, size: int = 1600):
    """Browser-friendly JPEG of an image (handles HEIC + EXIF rotation)."""
    m = _meta_or_404(fid)
    if m["kind"] != "image":
        raise HTTPException(400, "not an image")
    size = max(200, min(size, 4000))
    p = config.THUMBS / f"{fid}_{size}.jpg"
    if not p.exists():
        im = load_image(storage.original_path(fid)).convert("RGB")
        im.thumbnail((size, size), Image.LANCZOS)
        im.save(p, quality=88)
    return FileResponse(p)


# ------------------------------------------------------------------ settings (brand + property)

@app.get("/api/settings")
def get_settings():
    return storage.load_settings()


@app.put("/api/settings")
def put_settings(s: dict):
    return storage.save_settings(s)


def _brand():
    s = storage.load_settings()
    logo_path, logo = None, None
    if s.get("logo_id"):
        try:
            logo_path = storage.original_path(s["logo_id"])
            logo = load_image(logo_path).convert("RGBA")
            # Ensure ffmpeg gets a PNG with alpha
            png = config.THUMBS / f"{s['logo_id']}_logo.png"
            if not png.exists():
                logo.save(png)
            logo_path = str(png)
        except KeyError:
            pass
    return s, logo, logo_path


@app.get("/api/styles")
def styles():
    return {"styles": STYLES, "photo_defaults": PHOTO_DEFAULTS,
            "photo_formats": list(photo.FORMATS), "video_presets": list(video.PRESETS),
            "transitions": sorted(video.TRANSITIONS)}


# ------------------------------------------------------------------ photo

class AnalyzeReq(BaseModel):
    file_id: str
    style: str | None = None


@app.post("/api/photo/analyze")
def photo_analyze(r: AnalyzeReq):
    m = _meta_or_404(r.file_id)
    if m["kind"] != "image":
        raise HTTPException(400, "not an image")
    return analyze.analyze_photo(storage.original_path(r.file_id), r.style)


class PhotoReq(BaseModel):
    file_ids: list[str]
    params: dict = {}
    auto_each: bool = False      # analyse each photo and adapt the tone settings per photo
    style: str | None = None
    preview: bool = False
    masks: dict = {}             # file_id -> PNG data URL (object removal)
    output: str = "jpg"


@app.post("/api/photo/process")
def photo_process(r: PhotoReq):
    for fid in r.file_ids:
        if _meta_or_404(fid)["kind"] != "image":
            raise HTTPException(400, f"{fid} is not an image")
    brand, logo, _ = _brand()

    def work(job):
        n = len(r.file_ids)
        produced = []
        for i, fid in enumerate(r.file_ids):
            meta = storage.get_meta(fid)
            job.message = meta["name"]
            src = storage.original_path(fid)
            params = dict(r.params)
            if r.auto_each:
                a = analyze.analyze_photo(src, r.style)
                params.update(a["params"])       # tone & geometry from analysis
                for k, v in r.params.items():    # branding / format keep user values
                    if k not in PHOTO_DEFAULTS:
                        params[k] = v
            params["inpaint_mask"] = r.masks.get(fid)
            cb = lambda f, i=i: job.set_progress(100 * (i + f) / n)
            max_size = 1400 if r.preview else None
            out = photo.process(src, params, brand, logo, max_size=max_size, progress=cb)
            stem = Path(meta["name"]).stem
            fmt = params.get("format", "original")
            if r.output == "png" and not r.preview:
                path = job.out_dir / f"{stem}_albasmah.png"
                out.save(path, optimize=True)
            else:
                q = 80 if fmt == "whatsapp" else (85 if r.preview else 93)
                path = job.out_dir / f"{stem}_albasmah{'_preview' if r.preview else ''}.jpg"
                out.save(path, quality=q, subsampling=0 if q > 90 else 2, optimize=True)
            extra = {"width": out.width, "height": out.height}
            if r.preview:  # matching "before" image for the comparison slider
                before = load_image(src).convert("RGB")
                before.thumbnail((max_size, max_size), Image.LANCZOS)
                before = photo.frame_image(before, fmt, params.get("fit", "pad_blur"))
                bpath = job.out_dir / f"{stem}_before.jpg"
                before.save(bpath, quality=85)
                extra["before"] = f"/outputs/{job.id}/{bpath.name}"
            job.add_output(path, "image", source=fid, extra=extra)
            produced.append(path)
        if len(produced) > 1 and not r.preview:
            z = job.out_dir / "albasmah_photos.zip"
            with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
                for pth in produced:
                    zf.write(pth, pth.name)
            job.add_output(z, "zip")

    title = ("preview" if r.preview else "export") + f" {len(r.file_ids)} photo(s)"
    return jobs.submit("photo", title, work).to_dict()


# ------------------------------------------------------------------ video

@app.post("/api/video/analyze")
def video_analyze(r: AnalyzeReq):
    m = _meta_or_404(r.file_id)
    if m["kind"] != "video":
        raise HTTPException(400, "not a video")
    src = storage.original_path(r.file_id)
    return analyze.analyze_video(src, storage.video_info(src), r.style)


class VideoReq(BaseModel):
    clips: list[dict]            # [{file_id, start, end}] in order
    params: dict = {}
    preview: bool = False


@app.post("/api/video/render")
def video_render(r: VideoReq):
    if not r.clips:
        raise HTTPException(400, "no clips")
    for c in r.clips:
        if _meta_or_404(c.get("file_id", ""))["kind"] != "video":
            raise HTTPException(400, "clip is not a video")
    if r.params.get("music_id"):
        _meta_or_404(r.params["music_id"])
    if r.params.get("preset", "landscape_1080") not in video.PRESETS:
        raise HTTPException(400, "unknown preset")
    brand, _, logo_path = _brand()

    def work(job):
        out = video.render(job, r.clips, r.params, brand, logo_path, job.out_dir, preview=r.preview)
        info = storage.video_info(str(out))
        job.add_output(out, "video", extra={"width": info.get("width"), "height": info.get("height"),
                                            "duration": info.get("duration")})

    title = ("preview" if r.preview else "export") + f" video ({len(r.clips)} clip(s))"
    return jobs.submit("video", title, work).to_dict()


# ------------------------------------------------------------------ jobs

@app.get("/api/jobs")
def list_jobs():
    return jobs.list_jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(404)
    return j


@app.get("/api/health")
def health():
    return {"ok": True}


app.mount("/outputs", StaticFiles(directory=config.OUTPUTS), name="outputs")
app.mount("/", StaticFiles(directory=config.FRONTEND, html=True), name="frontend")
