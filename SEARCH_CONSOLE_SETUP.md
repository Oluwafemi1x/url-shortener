# Google Search Console setup

Property type: URL-prefix

Property URL:
https://oluwafemi1x.github.io/url-shortener/

Why URL-prefix:
The site is hosted under a GitHub Pages subpath, and Google Search Console URL-prefix properties can include a path.

Verification:
Use the HTML tag or HTML file method provided by Google Search Console.
Do not invent or modify the verification token. Add the exact token/file Google gives you.

Sitemap:
https://oluwafemi1x.github.io/url-shortener/sitemap.xml

Priority URLs to inspect after verification:
- https://oluwafemi1x.github.io/url-shortener/
- https://oluwafemi1x.github.io/url-shortener/qr-code-generator/
- https://oluwafemi1x.github.io/url-shortener/utm-builder/
- https://oluwafemi1x.github.io/url-shortener/url-expander/
- https://oluwafemi1x.github.io/url-shortener/link-tracker/
- https://oluwafemi1x.github.io/url-shortener/guides/what-is-a-url-shortener/
- https://oluwafemi1x.github.io/url-shortener/guides/how-to-shorten-a-url/
- https://oluwafemi1x.github.io/url-shortener/guides/utm-parameters-explained/

After verification:
1. Submit sitemap.xml.
2. Use URL Inspection on the homepage and the main tool pages.
3. Request indexing only after confirming the rendered page is accessible and canonical is correct.
4. Monitor Indexing, Performance and Security reports.

Official references:
https://support.google.com/webmasters/answer/34592
https://support.google.com/webmasters/answer/9008080
https://developers.google.com/search/docs/appearance/structured-data/software-app

## Current verification and free hosting (October 4, 2026)

The existing Google HTML verification tag is preserved. Google's URL Inspection API reports the homepage **Submitted and indexed**, crawl allowed, last crawl September 28, 2026 at 21:27:27 UTC. The ten existing tool/use-case/guide pages inspected on October 4 were **URL is unknown to Google**. Performance data through September 29 contains zero impressions and clicks. These are indexing/performance results, not guarantees about the new deployment.

GSC Wizard's `list_sites` returned an empty list even though the property was already registered and activated. Direct URL Inspection, sitemap and query tools worked. Do not interpret an empty property listing as proof that verification was lost. Named query clusters are now configured for URL shortening and campaign/QR searches.

On GitHub Pages, crawlers consult `https://oluwafemi1x.github.io/robots.txt`, not the copy under `/url-shortener/`. The host-root file currently returns 404, which imposes no robots restrictions. The project-level robots file documents the sitemap but cannot enforce rules for the host. Submit the sitemap directly in Search Console.

IndexNow uses its supported `keyLocation` option for the public key file inside `/url-shortener/`. A 200 receipt means the submission was received; a 202 means key validation is pending. Neither proves indexing. Google does not use this IndexNow notification as a general website indexing API.

Bing Webmaster Tools is not configured in the connected GSC Wizard account. To get Bing inspection and performance data, verify the same site in Bing Webmaster Tools and connect its API key to GSC Wizard. Keep account/API secrets out of this public repository. The existing public IndexNow key is an ownership file, not a password to a user account.

## Acceptance and monitoring

Run `python scripts/seo.py --live` after a deployment. Preserve its result alongside the IndexNow receipt. Inspect the homepage, the use-case pages and the guide hub in Search Console after they have been published. Request indexing through Google's own UI only where warranted; do not continually resubmit unchanged URLs.

Compare impressions, query rows, clicks and CTR for successive settled 28-day periods. Google metrics lag; never treat missing fresh data as a confirmed ranking loss. Inspect a page's canonical and crawl state when impressions disappear. The API wrapper currently returns verdict/crawl fields without Google's selected-canonical or rendered-page detail, so those fields require the native URL Inspection UI for full confirmation.
