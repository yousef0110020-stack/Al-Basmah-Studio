"""Password login with a signed session cookie (works in iPhone Safari and home-screen PWA).
Enable by setting STUDIO_PASSWORD. Login attempts are rate-limited per IP."""
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from . import config

COOKIE = "albasmah_session"
MAX_AGE = 30 * 24 * 3600
PUBLIC_PATHS = {"/login.html", "/api/login", "/manifest.webmanifest", "/sw.js", "/style.css", "/api/health",
                "/favicon.ico", "/offline.html"}
PUBLIC_PREFIXES = ("/icons/", "/fonts/")
_fails: dict = defaultdict(deque)


def _secret() -> bytes:
    import os
    env = os.environ.get("STUDIO_SECRET")
    if env:
        return env.encode()
    f = config.DATA_DIR / ".session_secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        f.chmod(0o600)
    # the password is mixed in, so changing the password logs everyone out
    return (f.read_text().strip() + config.PASSWORD).encode()


def enabled() -> bool:
    return bool(config.PASSWORD)


def make_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_secret(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    ts, sig = token.split(".", 1)
    good = hmac.new(_secret(), ts.encode(), hashlib.sha256).hexdigest()
    try:
        fresh = time.time() - int(ts) < MAX_AGE
    except ValueError:
        return False
    return fresh and hmac.compare_digest(sig, good)


def is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def too_many(ip: str) -> bool:
    q = _fails[ip]
    now = time.time()
    while q and now - q[0] > 900:
        q.popleft()
    return len(q) >= 10


def record_fail(ip: str):
    _fails[ip].append(time.time())


def check_password(pw: str) -> bool:
    return secrets.compare_digest((pw or "").encode(), config.PASSWORD.encode())
