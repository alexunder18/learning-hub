import re
import time
import hmac
import hashlib
import secrets
import threading
from functools import wraps
from urllib.parse import urlparse

from flask import request, session, redirect, jsonify, abort

from .config import load_config

SESSION_TIMEOUT = 30 * 60


def hash_pin(pin):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"


def verify_pin(pin, stored):
    if not stored or ":" not in stored:
        return False
    salt, h = stored.split(":", 1)
    check = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100000)
    return hmac.compare_digest(check.hex(), h)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cfg = load_config()
        if not cfg:
            return redirect("/setup")
        if cfg.get("pin_hash"):
            if not session.get("authenticated"):
                return redirect("/login")
            if time.time() - session.get("last_active", 0) > SESSION_TIMEOUT:
                session.clear()
                return redirect("/login")
            session["last_active"] = time.time()
        return f(*args, **kwargs)
    return decorated


def require_auth_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cfg = load_config()
        if cfg and cfg.get("pin_hash"):
            if not session.get("authenticated"):
                return jsonify({"error": "Not authenticated"}), 401
            if time.time() - session.get("last_active", 0) > SESSION_TIMEOUT:
                session.clear()
                return jsonify({"error": "Session expired"}), 401
            session["last_active"] = time.time()
        return f(*args, **kwargs)
    return decorated


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def require_csrf(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-CSRF-Token") or (request.json or {}).get("_csrf")
        if not token or token != session.get("csrf_token"):
            abort(403)
        return f(*args, **kwargs)
    return decorated


_rate_limits = {}
_rate_lock = threading.Lock()


def rate_limit(max_requests=10, window=60):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = f"{f.__name__}:{request.remote_addr}"
            now = time.time()
            with _rate_lock:
                entries = _rate_limits.get(key, [])
                entries = [t for t in entries if now - t < window]
                if len(entries) >= max_requests:
                    return jsonify({"error": "Too many requests. Please wait."}), 429
                entries.append(now)
                _rate_limits[key] = entries
            return f(*args, **kwargs)
        return decorated
    return decorator


ALLOWED_API_BASES = [
    r"^https://api\.anthropic\.com",
    r"^https://api\.openai\.com",
    r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    r"^http://ollama(:\d+)?$",
    r"^http://host\.docker\.internal(:\d+)?$",
]


def validate_api_base(url):
    if not url:
        return True
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return any(re.match(p, url) for p in ALLOWED_API_BASES)


_DANGEROUS_JS = re.compile(
    r"\b(fetch|XMLHttpRequest|import\s*\(|eval\s*\(|Function\s*\(|document\.cookie|"
    r"window\.location\s*=|location\.href\s*=|document\.write|\.src\s*=|"
    r"new\s+WebSocket|navigator\.sendBeacon|localStorage|sessionStorage)",
    re.IGNORECASE,
)


def sanitize_lesson_html(html):
    def clean_script(m):
        if _DANGEROUS_JS.search(m.group(1)):
            return "<!-- removed -->"
        return m.group(0)

    html = re.sub(r"<script\b[^>]*>(.*?)</script>", clean_script, html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script\b[^>]*\bsrc\s*=\s*[^>]*>.*?</script>", "<!-- removed -->", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "<!-- removed -->", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"javascript\s*:", "", html, flags=re.IGNORECASE)
    return html
