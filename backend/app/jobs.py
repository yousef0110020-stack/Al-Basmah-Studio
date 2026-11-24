"""Background job runner with progress reporting."""
import json
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

from . import config

_pool = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)
_jobs: dict = {}
_lock = threading.Lock()


class Job:
    def __init__(self, kind: str, title: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.title = title
        self.status = "queued"
        self.progress = 0.0
        self.message = ""
        self.outputs: list = []
        self.error = None
        self.created = time.time()
        self.finished = None
        self.out_dir = config.OUTPUTS / self.id
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def set_progress(self, pct: float):
        self.progress = round(max(self.progress, min(99.0, pct)), 1)

    def add_output(self, path, kind, source=None, extra=None):
        rel = path.relative_to(config.OUTPUTS).as_posix()
        item = {"name": path.name, "url": f"/outputs/{rel}", "kind": kind, "size": path.stat().st_size}
        if source:
            item["source"] = source
        if extra:
            item.update(extra)
        self.outputs.append(item)

    def to_dict(self):
        return {k: getattr(self, k) for k in
                ("id", "kind", "title", "status", "progress", "message", "outputs", "error", "created", "finished")}

    def save(self):
        (config.JOBS / f"{self.id}.json").write_text(json.dumps(self.to_dict(), ensure_ascii=False))


def submit(kind: str, title: str, fn) -> Job:
    job = Job(kind, title)
    with _lock:
        _jobs[job.id] = job

    def run():
        job.status = "running"
        try:
            fn(job)
            job.status = "done"
            job.progress = 100.0
        except Exception as e:  # report the error to the UI
            job.status = "error"
            job.error = str(e)[-2000:]
            traceback.print_exc()
        job.finished = time.time()
        job.save()

    _pool.submit(run)
    return job


def get(job_id: str):
    j = _jobs.get(job_id)
    if j:
        return j.to_dict()
    p = config.JOBS / f"{job_id}.json"
    if job_id.isalnum() and p.exists():
        return json.loads(p.read_text())
    return None


def list_jobs(limit=50):
    items = {j.id: j.to_dict() for j in _jobs.values()}
    for p in config.JOBS.glob("*.json"):
        if p.stem not in items:
            items[p.stem] = json.loads(p.read_text())
    return sorted(items.values(), key=lambda j: j["created"], reverse=True)[:limit]
