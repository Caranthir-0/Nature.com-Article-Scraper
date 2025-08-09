import os
import re
import time
import json
import string
import argparse
from pathlib import Path
from urllib.parse import urljoin
from typing import Optional, Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

BASE_URL = "https://www.nature.com"

PUNCT_TABLE = str.maketrans("", "", string.punctuation)
WINDOWS_RESERVED = {"CON","PRN","AUX","NUL","COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8","COM9",
                    "LPT1","LPT2","LPT3","LPT4","LPT5","LPT6","LPT7","LPT8","LPT9"}

def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0; +https://example.org/)",
        "Accept": "text/html,application/xhtml+xml",
    })
    retries = Retry(
        total=5, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def sanitize_filename(title: str, max_len: int = 120) -> str:
    base = title.strip()
    base = re.sub(r"\s+", " ", base)             # collapse whitespace
    base = base.translate(PUNCT_TABLE).replace(" ", "_")
    base = re.sub(r"[^A-Za-z0-9_\-]+", "", base) # keep safe chars
    if not base:
        base = "untitled"
    if base.upper() in WINDOWS_RESERVED:
        base = f"_{base}_"
    return (base[:max_len]).rstrip("_")

def extract_title(soup: BeautifulSoup) -> str:
    """Best-effort title extraction that avoids accidentally returning the literal string 'content'."""
    # Try common meta tags first
    for selector, attr in [
        ('meta[property="og:title"]', "content"),
        ('meta[name="dc.title"]', "content"),
        ('meta[name="citation_title"]', "content"),
        ('meta[name="twitter:title"]', "content"),
    ]:
        tag = soup.select_one(selector)
        if tag:
            val = (tag.get(attr) or "").strip()
            # Guard against returning the attribute name or empty text
            if val and val.lower() != "content":
                return val

    # Fall back to common H1 locations on Nature
    for sel in [
        "h1.c-article-title",
        "h1[data-test='article-title']",
        "header.c-article-header h1",
        "article h1",
    ]:
        h1 = soup.select_one(sel)
        if h1:
            txt = h1.get_text(" ", strip=True)
            if txt:
                return txt

    # Finally, fall back to <title>, stripping common suffixes
    t = soup.find("title")
    txt = t.get_text(strip=True) if t else "No Title"
    return re.sub(r"\s*\|\s*Nature.*$", "", txt)

def extract_teaser_or_body(soup: BeautifulSoup) -> Tuple[str, Dict[str, Any]]:
    # Try meta descriptions first
    teaser = ""
    for selector, attr in [
        ("meta[property='og:description']", "content"),
        ("meta[name='description']", "content"),
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get(attr):
            teaser = tag.get(attr).strip()
            if teaser:
                break

    # Try visible teaser
    if not teaser:
        teaser_tag = soup.select_one("p.article__teaser, div.c-article-teaser p")
        if teaser_tag:
            teaser = teaser_tag.get_text(strip=True)

    # Try article body (free/HTML) as richer content
    body_parts = []
    for sel in [
        "div#content div.c-article-body",   # modern body container
        "div.c-article-body",
        "div[data-component='article-body']",
        "article div.article-item__body",   # older layout
    ]:
        body = soup.select_one(sel)
        if body:
            body_parts = [p.get_text(" ", strip=True) for p in body.select("p")]
            body_parts = [p for p in body_parts if p]
            if body_parts:
                break

    text = "\n\n".join(body_parts).strip()
    if not text:
        text = teaser.strip()
    if not text:
        text = "No content available."

    meta: Dict[str, Any] = {}
    pub = soup.select_one('meta[name="dc.date"]') or soup.select_one('meta[itemprop="datePublished"]')
    if pub and pub.get("content"):
        meta["published"] = pub["content"]
    t = soup.select_one('meta[name="dc.type"]') or soup.select_one('span[data-test="article.type"]')
    if t:
        meta["type"] = t.get("content", t.get_text(strip=True))
    return text, meta

def parse_listing(html: bytes) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for art in soup.find_all("article"):
        type_tag = art.find("span", attrs={"data-test": "article.type"})
        link_tag = art.find("a", attrs={"data-track-action": "view article"})
        if not link_tag or not link_tag.get("href"):
            continue
        url = urljoin(BASE_URL, link_tag["href"])
        art_type = type_tag.get_text(strip=True) if type_tag else None
        items.append({"url": url, "type": art_type})
    return items

def scrape_nature(pages: int, article_type: str, year: Optional[int], outdir: Path, delay: float = 0.8) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    session = build_session()
    seen = set()
    saved = 0
    meta_f = open(outdir / "metadata.jsonl", "a", encoding="utf-8")

    for page_num in range(1, pages + 1):
        dir_name = outdir / f"Page_{page_num}"
        url = f"{BASE_URL}/nature/articles?sort=PubDate"
        if year:
            url += f"&year={year}"
        url += f"&page={page_num}"

        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"[WARN] listing {page_num}: HTTP {resp.status_code}")
                continue
            listing = parse_listing(resp.content)
        except requests.RequestException as e:
            print(f"[ERROR] listing {page_num}: {e}")
            continue

        matched = [it for it in listing if (not article_type or (it["type"] or "").strip() == article_type)]
        if not matched:
            print(f"[INFO] Page {page_num}: no matches.")
            time.sleep(delay)
            continue

        dir_name.mkdir(exist_ok=True)

        for it in matched:
            url = it["url"]
            if url in seen:
                continue
            seen.add(url)

            try:
                aresp = session.get(url, timeout=20)
                if aresp.status_code != 200:
                    print(f"[WARN] article: HTTP {aresp.status_code} {url}")
                    continue
                asoup = BeautifulSoup(aresp.content, "html.parser")
                title = extract_title(asoup)
                text, meta = extract_teaser_or_body(asoup)
            except requests.RequestException as e:
                print(f"[ERROR] article fetch: {e} {url}")
                continue

            fname = sanitize_filename(title) or "article"
            # Debug: show extracted title and text length
            print(f"[DEBUG] Title extracted: {title!r} -> filename: {fname}.txt")
            print(f"[DEBUG] Extracted text length: {len(text)} chars from {url}")
            filepath = dir_name / f"{fname}.txt"

            # Avoid overwriting by adding a short hash if needed
            if filepath.exists():
                suffix = hex(abs(hash(url)) % (16**6))[2:]
                filepath = dir_name / f"{fname}_{suffix}.txt"

            if not text.strip():
                text = "No content available."
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)

            rec = {"title": title, "url": url, "file": str(filepath.relative_to(outdir)), "page": page_num}
            rec.update(meta)
            rec["listed_type"] = it.get("type")
            meta_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            saved += 1
            time.sleep(delay)

        print(f"[OK] Page {page_num} processed: {len(matched)} matched.")

    meta_f.close()
    print(f"[DONE] Saved {saved} articles.")
    return saved

def main():
    parser = argparse.ArgumentParser(description="Scrape Nature listing pages.")
    parser.add_argument("--pages", type=int, required=True, help="Number of pages to scan")
    parser.add_argument("--type", type=str, default="", help="Exact article type to match (e.g., 'News')")
    parser.add_argument("--year", type=int, default=None, help="Filter by year (e.g., 2020)")
    parser.add_argument("--out", type=str, default="output", help="Output directory")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between requests in seconds")
    args = parser.parse_args()

    outdir = Path(args.out)
    scrape_nature(args.pages, args.type.strip(), args.year, outdir, delay=args.delay)

if __name__ == "__main__":
    main()