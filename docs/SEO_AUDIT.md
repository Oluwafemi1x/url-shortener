# Pycoder search visibility audit — October 4, 2026

Canonical homepage: https://oluwafemi1x.github.io/url-shortener/

## Verified baseline

- The live Pages frontend was serving an older `gh-pages` commit while recent changes were committed only to `main`.
- Google URL Inspection: homepage **PASS / Submitted and indexed**, robots **ALLOWED**, indexing **INDEXING_ALLOWED**, page fetch **SUCCESSFUL**, crawled as mobile on September 28, 2026 at 21:27:27 UTC.
- Ten inspected existing tool, use-case and guide pages: **URL is unknown to Google**, no recorded crawl. Unknown is distinct from a robots or noindex rejection.
- Search Console: zero clicks and impressions for September 6–29. No query rows; settled data is through September 29.
- Host-root robots.txt: HTTP 404. Project robots.txt does not control crawl policy at the host root. Root absence permits crawling by default.
- A made-up public path returned a genuine HTTP 404.
- Production `/health`: HTTP 200, persistent Supabase storage, shortening/redirect/analytics/QR/expansion features available.
- Bing Webmaster account API connection: not configured.

## Implemented

- 18 canonical public pages, including a guide hub and distinct custom-alias and social-sharing workflows.
- Unique titles/descriptions, one H1 per page, initial static HTML, Open Graph URL/title/description/type, structured data and breadcrumbs where relevant.
- Every public page reachable from homepage links; all local resources and fragments checked.
- Content-hash manifest and generated sitemap; unchanged page content retains its modification date.
- More legible mobile controls, visible tool navigation, keyboard focus and reduced-motion support.
- Shortening tolerates blocked/full local history storage. Copy actions show manual-copy guidance if blocked. Shortening and QR requests use bounded 60-second waits; QR submission prevents duplicate clicks.
- README describes the real first-party Flask backend and current limits. Public tool claims no longer promise permanent service availability or editable destinations.
- CI validates SEO architecture. Publishing exports public files only, requests a Pages build, verifies deployed source and stores IndexNow receipts. Changed public HTML URLs are notified once per successful publication.
- Search Console branded terms and two topic clusters configured for measured follow-up.

## Acceptance evidence

Source checks: 18 pages pass unique metadata, canonical, JSON-LD syntax, resource, fragment and link-graph checks. JavaScript syntax checks pass. Existing 15 backend unit tests pass.

Deployment, live browser, IndexNow and sitemap results are recorded below after publication.

## Limits that remain external

Technical checks cannot promise search ranking or a crawl date. Bing account verification needs account access. Search Console's available inspection wrapper does not expose Google's selected canonical or rendered HTML; native inspection is needed for those details. GitHub Pages branch hosting cannot issue custom server redirects for `/index.html`; self-canonicals and consistent internal links identify the preferred slash URLs. Genuine third-party community mentions cannot be manufactured and have not been claimed.
