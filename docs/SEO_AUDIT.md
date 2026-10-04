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

Technical checks cannot promise search ranking or a crawl date. Bing ownership is verified; crawl, indexing and report availability remain Bing's decisions. Search Console's available inspection wrapper does not expose Google's selected canonical or rendered HTML; native inspection is needed for those details. GitHub Pages branch hosting cannot issue custom server redirects for `/index.html`; self-canonicals and consistent internal links identify the preferred slash URLs. Genuine third-party community mentions cannot be manufactured and have not been claimed.

## Publication and live verification results

- Source commit: `d657b73f77560e57dc07dfe672003424ed12a49e`.
- [CI passed](https://github.com/Oluwafemi1x/url-shortener/actions/runs/37218233430).
- [Automatic publication passed](https://github.com/Oluwafemi1x/url-shortener/actions/runs/37218325676), including explicit Pages build request, source-version confirmation, all live page checks and artifact preservation.
- Published Pages commit: `84bc732f609dfb08f079e4219ef4ffa7f14d8ca5`; [Pages deployment passed](https://github.com/Oluwafemi1x/url-shortener/actions/runs/37218336347).
- Live audit: all 18 pages HTTP 200, exact tested HTML, canonical and metadata checks passed. Googlebot and Bingbot user-agent requests received the same static homepage. Sitemap and JS/CSS/favicon assets matched tested files. A nonexistent page returned 404.
- IndexNow at 16:52:27 UTC: HTTP **200**, outcome **received**, covering the 18 changed public pages. This records submission receipt, not Bing indexing.
- Google accepted the updated sitemap at 16:54:30 UTC; fetch/processing still pending at submission.
- New guide hub, custom-alias and social-sharing pages added to the indexing tracker. Two named search-query clusters and branded terms are configured.
- Live browser: shortening produced `https://pyc0.onrender.com/EeIUW` for the public example destination; copy returned that exact URL; QR loaded as a 296-pixel PNG; the short URL returned HTTP 302 to the intended destination.
- Desktop screenshot checked for legible, unclipped layout. Mobile rules were improved, but a narrow-viewport browser test could not be completed: the local browser executable was unavailable and the cloud browser did not expose viewport resizing. Mobile visual acceptance remains unverified.
- Bing Webmaster Tools ownership verified on 4 October 2026 using the published `msvalidate.01` homepage tag. Sitemap submitted successfully; status Processing, zero reported errors/warnings, zero discovered URLs at submission. Reports may take up to 48 hours.
- Bing homepage inspection: **Discovered but not crawled**, discovered 24 September 2026. Bing live test: **URL can be indexed by Bing**, **No SEO/GEO issues found**, two markup types detected. Eligibility is not indexing.
- Ownership-tag source commit: `953a39a2d32899222148ec37e05100eb698d10ce`. [CI passed](https://github.com/Oluwafemi1x/url-shortener/actions/runs/37219674389); [publication and live validation passed](https://github.com/Oluwafemi1x/url-shortener/actions/runs/37219710807); [Pages deployment passed](https://github.com/Oluwafemi1x/url-shortener/actions/runs/37219723672). Independent 18-page live audit passed after deployment.
- The GitHub profile now includes a descriptive link to the live shortener. No community postings or fabricated third-party mentions were used.
