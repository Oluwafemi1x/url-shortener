"""Build the public sitemap and check source or live pages using the standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://oluwafemi1x.github.io/url-shortener/"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
EXCLUDED = {"backend", "scripts", "node_modules", ".git", ".github"}


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.meta, self.links, self.assets, self.ids = {}, [], [], []
        self.canonicals, self.h1s, self.schemas, self.images = [], [], [], []
        self.title, self.text, self.lang = "", [], ""
        self.current, self.buffer = None, []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html": self.lang = attrs.get("lang", "")
        if "id" in attrs: self.ids.append(attrs["id"])
        if tag == "meta": self.meta[attrs.get("name", attrs.get("property", ""))] = attrs.get("content", "")
        if tag == "link":
            if attrs.get("rel") == "canonical": self.canonicals.append(attrs.get("href"))
            elif attrs.get("href"): self.assets.append(attrs["href"])
        if tag == "a" and attrs.get("href"): self.links.append(attrs["href"])
        if tag == "script" and attrs.get("src"): self.assets.append(attrs["src"])
        if tag == "img":
            self.images.append(attrs)
            if attrs.get("src"): self.assets.append(attrs["src"])
        if tag in {"title", "h1"} or tag == "script" and attrs.get("type") == "application/ld+json":
            self.current, self.buffer = tag, []

    def handle_data(self, data):
        if self.current: self.buffer.append(data)
        self.text.append(data)

    def handle_endtag(self, tag):
        if self.current != tag: return
        content = "".join(self.buffer).strip()
        if tag == "title": self.title = content
        elif tag == "h1": self.h1s.append(content)
        elif tag == "script": self.schemas.append(json.loads(content))
        self.current = None


def pages():
    return sorted(p for p in ROOT.rglob("index.html") if not any(part in EXCLUDED or part.startswith(".") for part in p.relative_to(ROOT).parts))


def canonical(path):
    parent = path.relative_to(ROOT).parent.as_posix()
    return BASE + (parent + "/" if parent != "." else "")


def build(write=False):
    manifest_path = ROOT / "seo-manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest = {}
    root = ET.Element("urlset", xmlns=NS)
    for path in pages():
        relative = path.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        old = previous.get(relative, {})
        modified = old.get("lastmod", str(date.today())) if old.get("sha256") == digest else str(date.today())
        manifest[relative] = {"sha256": digest, "lastmod": modified}
        entry = ET.SubElement(root, "url")
        ET.SubElement(entry, "loc").text = canonical(path)
        ET.SubElement(entry, "lastmod").text = modified
    ET.indent(root, space="  ")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if write:
        (ROOT / "sitemap.xml").write_text(xml)
        manifest_path.write_text(encoded)
    else:
        assert (ROOT / "sitemap.xml").read_text() == xml, "Sitemap needs rebuilding: python scripts/seo.py --write"
        assert manifest_path.read_text() == encoded, "Content manifest is stale: python scripts/seo.py --write"
    return list(manifest)


def validate_page(html, expected, titles=None, descriptions=None):
    page = Page(html)
    assert page.lang == "en", f"{expected}: missing language"
    assert page.title and len(page.title) <= 90, f"{expected}: invalid title"
    assert len(page.h1s) == 1 and page.h1s[0], f"{expected}: expected one H1"
    assert page.meta.get("description"), f"{expected}: missing description"
    assert "noindex" not in page.meta.get("robots", "").lower(), f"{expected}: noindex"
    assert page.canonicals == [expected], f"{expected}: incorrect canonical {page.canonicals}"
    assert page.meta.get("viewport"), f"{expected}: no viewport"
    assert page.meta.get("og:url") == expected, f"{expected}: incorrect OG URL"
    for name in ["og:title", "og:description", "og:type"]:
        assert page.meta.get(name), f"{expected}: missing {name}"
    assert len(page.ids) == len(set(page.ids)), f"{expected}: duplicate IDs"
    assert page.schemas, f"{expected}: no structured data"
    for schema in page.schemas:
        assert schema.get("@context") == "https://schema.org", f"{expected}: invalid schema context"
    for image in page.images: assert "alt" in image, f"{expected}: image lacks alt text"
    if titles is not None:
        assert page.title not in titles, f"{expected}: duplicate title"
        titles.add(page.title)
        assert page.meta["description"] not in descriptions, f"{expected}: duplicate description"
        descriptions.add(page.meta["description"])
    return page


def local_check():
    build()
    parsed, titles, descriptions = {}, set(), set()
    for path in pages(): parsed[canonical(path)] = validate_page(path.read_text(), canonical(path), titles, descriptions)
    graph = {url: set() for url in parsed}
    for url, page in parsed.items():
        for value in page.links + page.assets:
            target = urljoin(url, value)
            if not target.startswith(BASE): continue
            bits = urlsplit(target)
            relative = unquote(bits.path[len(urlsplit(BASE).path):])
            path = ROOT / relative
            if bits.path.endswith("/"): path /= "index.html"
            assert path.is_file(), f"{url}: broken resource {value}"
            clean = target.split("#")[0].split("?")[0]
            if clean in graph: graph[url].add(clean)
            if bits.fragment and target.startswith(BASE) and path.suffix == ".html":
                ids = Page(path.read_text()).ids
                assert bits.fragment in ids, f"{url}: missing fragment {value}"
    seen, queue = set(), [BASE]
    while queue:
        url = queue.pop()
        if url in seen: continue
        seen.add(url); queue.extend(graph[url] - seen)
    assert seen == set(parsed), f"Orphan pages: {set(parsed) - seen}"
    assert BASE + "sitemap.xml" in (ROOT / "robots.txt").read_text()
    print(f"PASS: {len(parsed)} public pages; unique metadata, canonicals, schema, resources, fragments and reachability.")


def fetch(url, user_agent="PycoderSEOCheck/1.0"):
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.status, response.geturl(), response.headers, response.read()


def live_check():
    results = []
    def check(path):
        url = canonical(path)
        status, final, headers, body = fetch(url)
        assert status == 200 and final == url, f"{url}: unexpected HTTP status/redirect"
        assert "text/html" in headers.get("Content-Type", ""), f"{url}: not HTML"
        assert "noindex" not in headers.get("X-Robots-Tag", "").lower(), f"{url}: HTTP noindex"
        page = validate_page(body.decode(), url)
        assert len(page.text) > 20, f"{url}: empty initial HTML"
        assert body == path.read_bytes(), f"{url}: deployed content differs from tested source"
        return {"url": url, "status": status, "bytes": len(body), "canonical": page.canonicals[0], "sourceMatches": True}
    with ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(check, pages()))
    _, _, _, xml = fetch(BASE + "sitemap.xml")
    assert xml == (ROOT / "sitemap.xml").read_bytes(), "Live sitemap differs from source"
    host_root = "https://" + urlsplit(BASE).netloc + "/robots.txt"
    try:
        _, _, _, body = fetch(host_root)
        robots = urllib.robotparser.RobotFileParser(); robots.parse(body.decode().splitlines())
        for row in results:
            for bot in ["Googlebot", "Bingbot"]: assert robots.can_fetch(bot, row["url"]), f"Robots blocks {bot}"
        robots_status = "root robots.txt permits all public pages"
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, f"Root robots returned {exc.code}"
        robots_status = "root robots.txt is 404: no crawl restrictions; subpath robots.txt is not authoritative"
    for bot in ["Googlebot", "Bingbot"]:
        _, _, _, html = fetch(BASE, bot)
        validate_page(html.decode(), BASE)
        assert html == (ROOT / "index.html").read_bytes(), f"Different homepage HTML for {bot}"
    for path in ["missing-seo-check-page-404/", "404.html"]:
        if path == "404.html": continue
        try: fetch(BASE + path); raise AssertionError("Missing page must not return a soft 404")
        except urllib.error.HTTPError as exc: assert exc.code == 404
    for asset in ["app.js", "tools.js", "styles.css", "favicon.svg", "assets/pycoder-link-tools.svg"]:
        _, _, _, body = fetch(BASE + asset)
        assert body == (ROOT / asset).read_bytes(), f"Stale deployed asset: {asset}"
    print(json.dumps({"pages": results, "robots": robots_status, "checks": "PASS"}, indent=2))


def export(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in EXCLUDED or part.startswith(".") for part in relative.parts): continue
        if path.suffix not in {".html", ".css", ".js", ".svg", ".png", ".ico", ".txt"} and relative.as_posix() != "sitemap.xml": continue
        if path.name in {"requirements.txt", "pages-deploy.txt"}: continue
        target = destination / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (destination / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--export")
    args = parser.parse_args()
    if args.write: build(True)
    local_check()
    if args.live: live_check()
    if args.export: export(args.export)
