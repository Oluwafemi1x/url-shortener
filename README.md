# Pycoder URL Shortener

A polished, responsive URL-shortening application by **Olawumi Oluwafemi (Pycoder)**.

The live GitHub Pages frontend creates permanent short links through the documented **is.gd URL Shortening API**. The repository also includes an optional **Flask + SQLite backend** for self-hosting your own short-link service with persistent storage and redirect tracking.

## Live demo

**https://oluwafemi1x.github.io/url-shortener/**

> If GitHub Pages has not been enabled yet, select the `gh-pages` branch and `/ (root)` under **Settings → Pages**.

## Features

- Create permanent short URLs
- Optional custom aliases
- Optional is.gd link statistics
- Copy, open and share actions
- Browser-local recent-link history
- URL and alias validation
- Responsive mobile/desktop interface
- Graceful network and API error handling
- Persistent Flask + SQLite self-hosted backend
- Parameterized SQL queries
- Collision-safe short-code generation
- Redirect click tracking
- Automated CI checks

## Architecture

### GitHub Pages frontend

The live frontend is intentionally static so it can run reliably on GitHub Pages.

```text
index.html
styles.css
app.js
```

When a visitor submits a URL, `app.js` calls the public is.gd API using its documented JSONP callback support. This avoids the broken `localhost:5000` dependency that existed in the original prototype.

The frontend stores only recent link history in the visitor's own browser using `localStorage`. It does not upload that local history to this repository.

### Optional self-hosted Python API

The `backend/` directory contains a standalone Flask service with SQLite persistence.

```text
backend/
├── __init__.py
├── app.py
├── requirements.txt
└── test_app.py
```

API endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/shorten` | Create or reuse a short URL |
| `GET` | `/api/links/<code>` | Read link metadata |
| `GET` | `/<code>` | Redirect to the original URL |

Example request:

```bash
curl -X POST http://127.0.0.1:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/a/long/path","custom_alias":"pycoder1"}'
```

Example response:

```json
{
  "code": "pycoder1",
  "short_url": "http://127.0.0.1:5000/pycoder1",
  "original_url": "https://example.com/a/long/path",
  "clicks": 0,
  "created": true
}
```

## Run the frontend locally

No build step is required.

```bash
python -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Run the Flask backend locally

Create and activate a virtual environment, then install the backend requirements.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m backend.app
```

The API will start at:

```text
http://127.0.0.1:5000
```

## Backend configuration

Optional environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_PATH` | `backend/url_shortener.db` | SQLite database file |
| `PUBLIC_BASE_URL` | Request host | Public base URL used in returned short links |
| `CORS_ORIGINS` | `*` | Comma-separated allowed frontend origins |
| `PORT` | `5000` | Flask development server port |

For a public production deployment, set `PUBLIC_BASE_URL` and restrict `CORS_ORIGINS`.

## Tests

Run:

```bash
python -m unittest backend.test_app -v
```

The test suite checks:

- health endpoint
- URL normalization
- short-link creation
- redirect behavior
- unsupported protocol rejection
- custom alias conflicts

## Why the old implementation was replaced

The previous Angular frontend called:

```text
http://localhost:5000/api/shorten
```

That only works when a Flask server is running on the visitor's own computer. The backend also used an in-memory dictionary, so all links disappeared after every restart.

This version removes those two failure points:

1. The GitHub Pages client uses a real public shortening service.
2. The optional Flask backend uses SQLite for persistent storage.

The original implementation is preserved on the branch:

```text
archive/angular-flask-prototype
```

## API provider

The hosted frontend uses the official is.gd API. Their API is intended for reasonable/low-volume use and is rate limited. See their developer documentation for current limits and terms.

## Security notes

- Only `http://` and `https://` targets are accepted by the self-hosted backend.
- SQL statements use parameterized queries.
- Custom aliases are validated before database insertion.
- Generated codes use Python's `secrets` module.
- Do not treat a URL shortener as a trust signal; always verify destinations before opening unfamiliar links.

## Author

**Olawumi Oluwafemi — Pycoder**

- GitHub: https://github.com/Oluwafemi1x
- Portfolio: https://oluwafemi1x.github.io/Task-Manager/

## License

MIT
