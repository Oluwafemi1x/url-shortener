from __future__ import annotations

import hmac
import ipaddress
import io
import json
import os
import re
import secrets
import sqlite3
import string
import time
from collections import defaultdict, deque
from contextlib import closing
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

import qrcode
from flask import Flask, jsonify, redirect, request, send_file, session
from flask_cors import CORS

CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{5,30}$")
ALPHABET = string.ascii_letters + string.digits
RESERVED_CODES = {"api", "health", "static", "admin"}
RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)
RATE_LOCK = Lock()


def normalize_url(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("URL must be a string.")

    raw = value.strip()
    if not raw:
        raise ValueError("URL is required.")

    if "://" not in raw:
        raw = "https://" + raw

    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise ValueError("Invalid URL.") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only http:// and https:// URLs are supported.")

    if not parsed.hostname:
        raise ValueError("URL must include a valid hostname.")

    normalized = urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            parsed.path or "",
            parsed.query,
            parsed.fragment,
        )
    )

    if len(normalized) > 5000:
        raise ValueError("URL is too long. Maximum length is 5,000 characters.")

    return normalized


def validate_destination_url(value: object, blocked_hosts: set[str] | None = None) -> str:
    normalized = normalize_url(value)
    parsed = urlsplit(normalized)
    host = (parsed.hostname or "").rstrip(".").lower()

    blocked = {"localhost", "0.0.0.0"}
    blocked.update(item.lower() for item in (blocked_hosts or set()) if item)
    if host in blocked or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("That destination host is not allowed.")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError("Private or local network destinations are not allowed.")

    return normalized


def validate_custom_code(value: object) -> str | None:
    if value in (None, ""):
        return None

    if not isinstance(value, str):
        raise ValueError("Custom alias must be a string.")

    code = value.strip()
    if not CODE_PATTERN.fullmatch(code):
        raise ValueError(
            "Custom aliases must be 5–30 letters, numbers, underscores or hyphens."
        )

    if code.lower() in RESERVED_CODES:
        raise ValueError("That custom alias is reserved.")

    return code


def generate_code(length: int = 5) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def connect_database(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(path: str) -> None:
    database_path = Path(path)
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect_database(path)) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                clicks INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_links_original_url ON links(original_url)"
        )
        db.commit()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)

    default_database = os.getenv(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "url_shortener.db"),
    )

    app.config.update(
        DATABASE_PATH=default_database,
        PUBLIC_BASE_URL=os.getenv("PUBLIC_BASE_URL", "").rstrip("/"),
        SUPABASE_STORE_URL=os.getenv("SUPABASE_STORE_URL", "").rstrip("/"),
        STORE_SHARED_SECRET=os.getenv("STORE_SHARED_SECRET", ""),
        ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD", ""),
        SECRET_KEY=os.getenv("ADMIN_SESSION_SECRET") or secrets.token_urlsafe(48),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        PERMANENT_SESSION_LIFETIME=8 * 60 * 60,
    )

    if test_config:
        app.config.update(test_config)

    cors_origins = os.getenv("CORS_ORIGINS", "*")
    origins = "*" if cors_origins.strip() == "*" else [
        item.strip() for item in cors_origins.split(",") if item.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    if not app.config["SUPABASE_STORE_URL"]:
        initialize_database(app.config["DATABASE_PATH"])

    def base_url() -> str:
        return app.config.get("PUBLIC_BASE_URL") or request.host_url.rstrip("/")

    def public_host() -> str:
        return (urlsplit(base_url()).hostname or "").lower()

    def blocked_hosts() -> set[str]:
        configured = {
            item.strip().lower()
            for item in os.getenv("BLOCKED_DESTINATION_HOSTS", "").split(",")
            if item.strip()
        }
        configured.add(public_host())
        return configured

    def client_id() -> str:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()[:80]
        return (request.remote_addr or "unknown")[:80]

    def rate_limited(scope: str, limit: int, window_seconds: int):
        now = time.monotonic()
        key = (scope, client_id())
        with RATE_LOCK:
            bucket = RATE_BUCKETS[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return jsonify({
                    "error": "Too many requests. Please try again shortly."
                }), 429, {"Retry-After": str(retry_after)}
            bucket.append(now)
        return None

    def store_call(action: str, **payload):
        url = app.config.get("SUPABASE_STORE_URL")
        if not url:
            return None

        shared_secret = app.config.get("STORE_SHARED_SECRET")
        if not shared_secret:
            raise RuntimeError("Persistent store authentication is not configured.")

        body = json.dumps({"action": action, **payload}).encode("utf-8")
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Pycoder-Store-Key": shared_secret,
            },
        )

        try:
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return response.status, data
        except HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8"))
            except Exception:
                data = {"error": "Persistent store request failed."}
            return exc.code, data
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("Persistent store is temporarily unavailable.") from exc

    def row_value(row, key: str, default=None):
        try:
            return row[key]
        except (KeyError, IndexError, TypeError):
            return default

    def serialize_row(row, created: bool = False) -> dict:
        return {
            "code": row["code"],
            "short_url": f"{base_url()}/{row['code']}",
            "original_url": row["original_url"],
            "clicks": row["clicks"],
            "created_at": row["created_at"],
            "created": created,
            "blocked": bool(row_value(row, "is_blocked", False)),
        }

    def find_by_code(code: str):
        remote = store_call("find_by_code", code=code)
        if remote is not None:
            status, data = remote
            if status >= 500:
                raise RuntimeError(data.get("error", "Persistent store request failed."))
            return data.get("link")

        with closing(connect_database(app.config["DATABASE_PATH"])) as db:
            return db.execute(
                "SELECT * FROM links WHERE code = ?",
                (code,),
            ).fetchone()

    def find_by_url(original_url: str):
        remote = store_call("find_by_url", original_url=original_url)
        if remote is not None:
            status, data = remote
            if status >= 500:
                raise RuntimeError(data.get("error", "Persistent store request failed."))
            return data.get("link")

        with closing(connect_database(app.config["DATABASE_PATH"])) as db:
            return db.execute(
                "SELECT * FROM links WHERE original_url = ? ORDER BY id ASC LIMIT 1",
                (original_url,),
            ).fetchone()

    def insert_link(code: str, original_url: str):
        remote = store_call("insert", code=code, original_url=original_url)
        if remote is not None:
            status, data = remote
            if status == 409:
                return None, True
            if status >= 400:
                raise RuntimeError(data.get("error", "Persistent store request failed."))
            return data.get("link"), False

        with closing(connect_database(app.config["DATABASE_PATH"])) as db:
            try:
                db.execute(
                    "INSERT INTO links (code, original_url) VALUES (?, ?)",
                    (code, original_url),
                )
                db.commit()
            except sqlite3.IntegrityError:
                return None, True

            row = db.execute(
                "SELECT * FROM links WHERE code = ?",
                (code,),
            ).fetchone()
            return row, False

    def referrer_host() -> str | None:
        value = request.headers.get("Referer", "").strip()
        if not value:
            return None
        try:
            host = urlsplit(value).hostname
        except ValueError:
            return None
        return host.lower()[:255] if host else None

    def device_type() -> str:
        ua = request.headers.get("User-Agent", "").lower()
        if not ua:
            return "other"
        if any(token in ua for token in ("bot", "crawler", "spider", "slurp")):
            return "bot"
        if "ipad" in ua or "tablet" in ua:
            return "tablet"
        if any(token in ua for token in ("iphone", "android", "mobile")):
            return "mobile"
        return "desktop"

    def record_click(code: str) -> None:
        remote = store_call(
            "record_click",
            code=code,
            referrer_host=referrer_host(),
            device_type=device_type(),
        )
        if remote is not None:
            status, data = remote
            if status >= 400:
                raise RuntimeError(data.get("error", "Analytics store request failed."))
            return

        with closing(connect_database(app.config["DATABASE_PATH"])) as db:
            db.execute(
                "UPDATE links SET clicks = clicks + 1 WHERE code = ?",
                (code,),
            )
            db.commit()

    def analytics_for(code: str) -> dict | None:
        remote = store_call("analytics", code=code)
        if remote is not None:
            status, data = remote
            if status == 404:
                return None
            if status >= 400:
                raise RuntimeError(data.get("error", "Analytics store request failed."))
            return data

        row = find_by_code(code)
        if not row:
            return None
        return {
            "link": serialize_row(row),
            "window_days": 30,
            "daily": [],
            "devices": [],
            "referrers": [],
        }

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "storage": "supabase" if app.config["SUPABASE_STORE_URL"] else "sqlite",
            "features": ["shorten", "redirect", "analytics", "qr", "expand", "abuse-reporting", "admin-dashboard"],
        }), 200

    @app.post("/api/shorten")
    def shorten_url():
        limited = rate_limited("shorten", 30, 60)
        if limited:
            return limited

        payload = request.get_json(silent=True) or {}

        try:
            original_url = validate_destination_url(
                payload.get("url"),
                blocked_hosts(),
            )
            custom_code = validate_custom_code(payload.get("custom_alias"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            if custom_code:
                existing = find_by_code(custom_code)

                if existing:
                    if row_value(existing, "is_blocked", False):
                        return jsonify({"error": "This destination has been disabled for safety or policy reasons."}), 403
                    if existing["original_url"] == original_url:
                        return jsonify(serialize_row(existing, created=False)), 200
                    return jsonify({"error": "That custom alias is already in use."}), 409

                row, collision = insert_link(custom_code, original_url)
                if collision:
                    return jsonify({"error": "That custom alias is already in use."}), 409
                return jsonify(serialize_row(row, created=True)), 201

            existing = find_by_url(original_url)
            if existing:
                if row_value(existing, "is_blocked", False):
                    return jsonify({"error": "This destination has been disabled for safety or policy reasons."}), 403
                return jsonify(serialize_row(existing, created=False)), 200

            for _ in range(30):
                candidate = generate_code()
                if find_by_code(candidate):
                    continue

                row, collision = insert_link(candidate, original_url)
                if not collision:
                    return jsonify(serialize_row(row, created=True)), 201

            return jsonify({"error": "Unable to generate a unique short code."}), 503
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

    @app.get("/api/links/<code>")
    def link_details(code: str):
        limited = rate_limited("details", 120, 60)
        if limited:
            return limited

        if not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Short URL not found."}), 404

        try:
            row = find_by_code(code)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

        if not row:
            return jsonify({"error": "Short URL not found."}), 404

        return jsonify(serialize_row(row)), 200

    @app.get("/api/analytics/<code>")
    def link_analytics(code: str):
        limited = rate_limited("analytics", 90, 60)
        if limited:
            return limited

        if not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Short URL not found."}), 404

        try:
            data = analytics_for(code)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

        if not data:
            return jsonify({"error": "Short URL not found."}), 404

        return jsonify(data), 200

    @app.post("/api/expand")
    def expand_short_url():
        limited = rate_limited("expand", 90, 60)
        if limited:
            return limited

        payload = request.get_json(silent=True) or {}
        value = payload.get("short_url")
        if not isinstance(value, str):
            return jsonify({"error": "Enter a Pycoder short URL."}), 400

        try:
            parsed = urlsplit(value.strip())
        except ValueError:
            return jsonify({"error": "Enter a valid Pycoder short URL."}), 400

        if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() != public_host():
            return jsonify({"error": "Only pyc0.onrender.com short links can be expanded here."}), 400

        code = parsed.path.strip("/")
        if "/" in code or not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Enter a valid Pycoder short URL."}), 400

        try:
            row = find_by_code(code)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

        if not row:
            return jsonify({"error": "Short URL not found."}), 404

        return jsonify(serialize_row(row)), 200

    @app.post("/api/report-abuse")
    def report_abuse():
        limited = rate_limited("abuse-report", 8, 3600)
        if limited:
            return limited

        payload = request.get_json(silent=True) or {}
        short_url = payload.get("short_url")
        reason = payload.get("reason")
        details = payload.get("details")

        if not isinstance(short_url, str):
            return jsonify({"error": "Enter the Pycoder short URL you want to report."}), 400

        try:
            parsed = urlsplit(short_url.strip())
        except ValueError:
            return jsonify({"error": "Enter a valid Pycoder short URL."}), 400

        if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() != public_host():
            return jsonify({"error": "Only Pycoder short links can be reported here."}), 400

        code = parsed.path.strip("/")
        if "/" in code or not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Enter a valid Pycoder short URL."}), 400

        allowed_reasons = {"phishing", "malware", "spam", "scam", "copyright", "other"}
        if reason not in allowed_reasons:
            return jsonify({"error": "Choose a valid report reason."}), 400

        if details is not None and not isinstance(details, str):
            return jsonify({"error": "Report details must be text."}), 400

        try:
            row = find_by_code(code)
            if not row:
                return jsonify({"error": "Short URL not found."}), 404

            remote = store_call(
                "report_abuse",
                short_url=f"{base_url()}/{code}",
                code=code,
                reason=reason,
                details=(details or "").strip()[:2000],
            )
            if remote is None:
                return jsonify({"error": "Abuse reporting requires persistent storage."}), 503

            status, data = remote
            if status >= 400:
                return jsonify({"error": data.get("error", "Unable to submit report.")}), 503
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

        return jsonify({"ok": True, "message": "Report received for review."}), 201


    def admin_required():
        if session.get("pycoder_admin") is True:
            return None
        return jsonify({"error": "Owner authentication required."}), 401

    @app.get("/admin/")
    def admin_dashboard():
        response = send_file(
            Path(__file__).resolve().parent / "admin_dashboard.html",
            mimetype="text/html",
        )
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none';"
        )
        return response

    @app.post("/api/admin/login")
    def admin_login():
        limited = rate_limited("admin-login", 5, 900)
        if limited:
            return limited

        configured = app.config.get("ADMIN_PASSWORD", "")
        payload = request.get_json(silent=True) or {}
        supplied = payload.get("password", "")

        if not configured:
            return jsonify({"error": "Owner login is not configured."}), 503

        if not isinstance(supplied, str) or not hmac.compare_digest(supplied, configured):
            return jsonify({"error": "Incorrect owner password."}), 401

        session.clear()
        session["pycoder_admin"] = True
        session.permanent = True
        return jsonify({"ok": True}), 200

    @app.post("/api/admin/logout")
    def admin_logout():
        session.clear()
        return jsonify({"ok": True}), 200

    @app.get("/api/admin/summary")
    def admin_summary():
        denied = admin_required()
        if denied:
            return denied
        remote = store_call("admin_summary")
        if remote is None:
            return jsonify({"error": "Owner dashboard requires persistent storage."}), 503
        status, data = remote
        return jsonify(data), status

    @app.get("/api/admin/links")
    def admin_links():
        denied = admin_required()
        if denied:
            return denied
        remote = store_call(
            "admin_links",
            q=request.args.get("q", "")[:300],
            blocked=request.args.get("blocked", "")[:10],
        )
        if remote is None:
            return jsonify({"error": "Owner dashboard requires persistent storage."}), 503
        status, data = remote
        return jsonify(data), status

    @app.get("/api/admin/reports")
    def admin_reports():
        denied = admin_required()
        if denied:
            return denied
        remote = store_call(
            "admin_reports",
            status=request.args.get("status", "open")[:20],
        )
        if remote is None:
            return jsonify({"error": "Owner dashboard requires persistent storage."}), 503
        status, data = remote
        return jsonify(data), status

    @app.post("/api/admin/links/<code>/block")
    def admin_set_block(code: str):
        denied = admin_required()
        if denied:
            return denied
        if not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Invalid short code."}), 400
        payload = request.get_json(silent=True) or {}
        blocked = payload.get("blocked")
        if not isinstance(blocked, bool):
            return jsonify({"error": "blocked must be true or false."}), 400
        reason = payload.get("reason")
        if reason is not None and not isinstance(reason, str):
            return jsonify({"error": "reason must be text."}), 400
        remote = store_call(
            "admin_set_block",
            code=code,
            blocked=blocked,
            reason=(reason or "").strip()[:500] if blocked else None,
        )
        if remote is None:
            return jsonify({"error": "Owner dashboard requires persistent storage."}), 503
        status, data = remote
        return jsonify(data), status

    @app.post("/api/admin/reports/<int:report_id>/status")
    def admin_set_report_status(report_id: int):
        denied = admin_required()
        if denied:
            return denied
        payload = request.get_json(silent=True) or {}
        value = payload.get("status")
        if value not in {"open", "reviewed", "dismissed", "blocked"}:
            return jsonify({"error": "Invalid report status."}), 400
        remote = store_call(
            "admin_set_report_status",
            report_id=report_id,
            status=value,
        )
        if remote is None:
            return jsonify({"error": "Owner dashboard requires persistent storage."}), 503
        status, data = remote
        return jsonify(data), status

    @app.post("/api/qr")
    def generic_qr():
        limited = rate_limited("qr-generic", 90, 60)
        if limited:
            return limited

        payload = request.get_json(silent=True) or {}
        try:
            target_url = normalize_url(payload.get("url"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        qr = qrcode.QRCode(version=None, box_size=8, border=4)
        qr.add_data(target_url)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")

        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)

        response = send_file(
            output,
            mimetype="image/png",
            as_attachment=False,
            download_name="pycoder-qr.png",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/qr/<code>.png")
    def link_qr(code: str):
        limited = rate_limited("qr", 90, 60)
        if limited:
            return limited

        if not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Short URL not found."}), 404

        try:
            row = find_by_code(code)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

        if not row:
            return jsonify({"error": "Short URL not found."}), 404

        qr = qrcode.QRCode(version=None, box_size=8, border=4)
        qr.add_data(f"{base_url()}/{code}")
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")

        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)

        response = send_file(
            output,
            mimetype="image/png",
            as_attachment=False,
            download_name=f"pycoder-{code}.png",
        )
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    @app.get("/<code>")
    def follow_short_url(code: str):
        if code.lower() in RESERVED_CODES or not CODE_PATTERN.fullmatch(code):
            return jsonify({"error": "Short URL not found."}), 404

        try:
            row = find_by_code(code)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503

        if not row:
            return jsonify({"error": "Short URL not found."}), 404

        if row_value(row, "is_blocked", False):
            return jsonify({
                "error": "This short link has been disabled for safety or policy reasons."
            }), 410

        try:
            record_click(code)
        except RuntimeError:
            # Analytics must never prevent the redirect itself.
            pass

        return redirect(row["original_url"], code=302)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not found."}), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
