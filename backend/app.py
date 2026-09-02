from __future__ import annotations

import os
import re
import secrets
import sqlite3
import string
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, jsonify, redirect, request
from flask_cors import CORS

CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{5,30}$")
ALPHABET = string.ascii_letters + string.digits
RESERVED_CODES = {"api", "health", "static"}


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


def generate_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def connect_database(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(path: str) -> None:
    database_path = Path(path)
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)

    with connect_database(path) as db:
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
    )

    if test_config:
        app.config.update(test_config)

    cors_origins = os.getenv("CORS_ORIGINS", "*")
    origins = "*" if cors_origins.strip() == "*" else [
        item.strip() for item in cors_origins.split(",") if item.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    initialize_database(app.config["DATABASE_PATH"])

    def base_url() -> str:
        return app.config.get("PUBLIC_BASE_URL") or request.host_url.rstrip("/")

    def link_payload(row: sqlite3.Row, created: bool = False) -> dict:
        return {
            "code": row["code"],
            "short_url": f"{base_url()}/{row['code']}",
            "original_url": row["original_url"],
            "clicks": row["clicks"],
            "created_at": row["created_at"],
            "created": created,
        }

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/api/shorten")
    def shorten_url():
        payload = request.get_json(silent=True) or {}

        try:
            original_url = normalize_url(payload.get("url"))
            custom_code = validate_custom_code(payload.get("custom_alias"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        with connect_database(app.config["DATABASE_PATH"]) as db:
            if custom_code:
                existing = db.execute(
                    "SELECT * FROM links WHERE code = ?",
                    (custom_code,),
                ).fetchone()

                if existing:
                    if existing["original_url"] == original_url:
                        return jsonify(link_payload(existing, created=False)), 200
                    return jsonify({"error": "That custom alias is already in use."}), 409

                code = custom_code
            else:
                existing = db.execute(
                    "SELECT * FROM links WHERE original_url = ? ORDER BY id ASC LIMIT 1",
                    (original_url,),
                ).fetchone()

                if existing:
                    return jsonify(link_payload(existing, created=False)), 200

                code = ""
                for _ in range(20):
                    candidate = generate_code()
                    collision = db.execute(
                        "SELECT 1 FROM links WHERE code = ?",
                        (candidate,),
                    ).fetchone()
                    if not collision:
                        code = candidate
                        break

                if not code:
                    return jsonify({"error": "Unable to generate a unique short code."}), 503

            db.execute(
                "INSERT INTO links (code, original_url) VALUES (?, ?)",
                (code, original_url),
            )
            db.commit()

            row = db.execute(
                "SELECT * FROM links WHERE code = ?",
                (code,),
            ).fetchone()

        return jsonify(link_payload(row, created=True)), 201

    @app.get("/api/links/<code>")
    def link_details(code: str):
        with connect_database(app.config["DATABASE_PATH"]) as db:
            row = db.execute(
                "SELECT * FROM links WHERE code = ?",
                (code,),
            ).fetchone()

        if not row:
            return jsonify({"error": "Short URL not found."}), 404

        return jsonify(link_payload(row)), 200

    @app.get("/<code>")
    def follow_short_url(code: str):
        if code.lower() in RESERVED_CODES:
            return jsonify({"error": "Short URL not found."}), 404

        with connect_database(app.config["DATABASE_PATH"]) as db:
            row = db.execute(
                "SELECT * FROM links WHERE code = ?",
                (code,),
            ).fetchone()

            if not row:
                return jsonify({"error": "Short URL not found."}), 404

            db.execute(
                "UPDATE links SET clicks = clicks + 1 WHERE code = ?",
                (code,),
            )
            db.commit()

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
