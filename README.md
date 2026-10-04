# Pycoder URL Shortener

[Use the free URL shortener](https://oluwafemi1x.github.io/url-shortener/) · [Read the guides](https://oluwafemi1x.github.io/url-shortener/guides/)

Pycoder turns a long HTTP or HTTPS address into a short redirect, with optional custom aliases and no signup. The static frontend runs on GitHub Pages and calls our Flask service at `https://pyc0.onrender.com`. Production link storage uses a Supabase service; the backend also supports SQLite for local development. The current frontend uses no third-party shortening-provider fallback.

## Try it

1. Paste your destination into the [shortening form](https://oluwafemi1x.github.io/url-shortener/#shortenForm).
2. Optionally choose an available alias of 5–30 letters, numbers, underscores or hyphens.
3. Copy the result and open it once to verify the destination.
4. Use the [QR generator](https://oluwafemi1x.github.io/url-shortener/qr-code-generator/) or [click tracker](https://oluwafemi1x.github.io/url-shortener/link-tracker/) when needed.

Generated codes have five characters. An identical destination may reuse an existing link. To compare campaign channels, add distinct UTM tags before shortening each destination. Link history is stored in the visitor's browser; disabled or full browser storage does not prevent shortening.

## Free tools and guides

| Task | Page |
| --- | --- |
| Create a short link without an account | [No-signup shortener](https://oluwafemi1x.github.io/url-shortener/free-url-shortener-no-signup/) |
| Choose a readable code | [Custom URL aliases](https://oluwafemi1x.github.io/url-shortener/custom-url-shortener/) |
| Share a campaign | [WhatsApp and social media guide](https://oluwafemi1x.github.io/url-shortener/url-shortener-for-social-media/) |
| Build campaign tags | [UTM builder](https://oluwafemi1x.github.io/url-shortener/utm-builder/) |
| Reveal a Pycoder destination | [URL expander](https://oluwafemi1x.github.io/url-shortener/url-expander/) |
| Learn the workflow | [How to shorten a URL](https://oluwafemi1x.github.io/url-shortener/guides/how-to-shorten-a-url/) |

A custom alias changes the code, not the domain. Public tools cannot reassign an existing alias or edit its destination. Short links do not protect private information; the privacy, acceptable-use and reporting pages explain current behavior. Analytics are counts of opens, not verified people or sales. Continued redirect availability depends on the service and destination remaining available.

## Local development

Serve the static files without a build step:

```bash
python -m http.server 8080
```

For the Python API:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
python -m backend.app
```

The API starts on port 5000. Main endpoints: `POST /api/shorten`, `GET /<code>`, `POST /api/expand`, `GET /api/analytics/<code>`, `POST /api/qr`, and `POST /api/report-abuse`. Owner APIs require authentication.

| Variable | Purpose |
| --- | --- |
| `PUBLIC_BASE_URL` | Public short-link origin |
| `CORS_ORIGINS` | Allowed frontend origins; restrict in production |
| `DATABASE_PATH` | Local SQLite file |
| `SUPABASE_STORE_URL` | Existing persistent storage service endpoint |
| `STORE_SHARED_SECRET` | Storage service authentication; keep private |
| `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET` | Owner access and session configuration |
| `PORT` | Server port |

## Validate and publish

```bash
python -m unittest backend.test_app -v
node --check app.js
node --check tools.js
python scripts/seo.py --write
python scripts/seo.py
```

Run `--write` after editing or adding public pages; it updates the content manifest and sitemap dates only when page content changes. Commit both generated files. The source checker verifies every public page's canonical, unique metadata, structured data, local resources and reachability from the homepage.

After CI passes on `main`, **Publish tested Pages** exports only public assets to `gh-pages`, explicitly requests a Pages build, checks the exact deployed source and notifies IndexNow of changed public HTML URLs. It preserves receipts as a workflow artifact. The manual IndexNow workflow is for an intentional full batch, not repeated submissions of unchanged URLs.

```bash
python scripts/seo.py --live
```

This checks the live HTML against tested source, bot responses, root robots behavior, static assets, sitemap and a genuine HTTP 404. Google's URL Inspection and Performance results remain separate from these technical checks. See [search-engine setup](SEARCH_CONSOLE_SETUP.md) and [the audit](docs/SEO_AUDIT.md).

## Author

[Olawumi Oluwafemi (Pycoder)](https://github.com/Oluwafemi1x) · [Portfolio](https://oluwafemi1x.github.io/Task-Manager/)

MIT license. The earlier Angular prototype remains on `archive/angular-flask-prototype`.
