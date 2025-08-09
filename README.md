Nature Article Scraper

A small, resilient scraper for nature.com listing pages. It walks through paginated article listings, fetches matching article pages, extracts a clean title and text (teaser or full HTML body when available), and saves each to a .txt file. It also writes a structured metadata.jsonl index for downstream processing.

Ethical use: Read and respect Nature’s Terms of Use and robots.txt. Scrape responsibly, add delays, and keep request volume low. Use this tool for personal/research purposes only.

⸻

Features
	•	Robust HTTP session with retries/backoff.
	•	Exact type filtering (e.g., News).
	•	Optional year filter via listing query.
	•	Clean filename sanitization (safe on Windows/macOS/Linux).
	•	Saves per-page folders and an indexed metadata.jsonl.
	•	Defensive parsing of titles and article bodies.

⸻

Requirements
	•	Python: 3.9+
	•	Packages: requests, beautifulsoup4

Install deps:

pip install -r requirements.txt

If you don’t have a requirements.txt, install directly:

pip install requests beautifulsoup4


⸻

Quick Start

Assuming the file is named scrape_nature.py (rename if needed):

python scrape_nature.py --pages 2

This scans the first 2 listing pages on nature.com/nature/articles?sort=PubDate and saves matches to ./output.

Common examples
	•	Only News articles from 2024, scan first 3 pages:

python scrape_nature.py --pages 3 --type News --year 2024


	•	Custom output folder and slower rate (1.5s delay):

python scrape_nature.py --pages 5 --out data/nature --delay 1.5


	•	All types, first page only (fast test):

python scrape_nature.py --pages 1



⸻

Command-line arguments

Flag	Type	Required	Default	Description
--pages	int	Yes	—	Number of listing pages to scan (1-based).
--type	str	No	""	Exact article type to match (e.g., News). Leave empty for all.
--year	int	No	None	Filter listing by year (e.g., 2020).
--out	str	No	output	Output directory. Created if missing.
--delay	float	No	0.8	Seconds to sleep between requests (politeness/backoff).

Note: Type matching is exact string match against the listing’s span[data-test="article.type"]. Examples: News, Research, Editorial, etc. (as shown by Nature’s UI).

⸻

What gets saved

Folder structure:

output/
  metadata.jsonl            # one JSON object per saved article
  Page_1/
    <sanitized_title>.txt
  Page_2/
    <sanitized_title>.txt
  ...

metadata.jsonl fields

Each line is a JSON object like:

{
  "title": "Article title",
  "url": "https://www.nature.com/...",
  "file": "Page_1/Article_title.txt",
  "page": 1,
  "published": "2024-09-14",      
  "type": "Research",              
  "listed_type": "News"            
}

Field notes:
	•	published – from meta[name="dc.date"] or itemprop="datePublished" if present.
	•	type – from meta[name="dc.type"] or the visible type tag if present.
	•	listed_type – the type shown on the listing page for that item.

Filenames and sanitization
	•	Titles are cleaned: whitespace collapsed, punctuation removed, non-safe characters stripped, spaces → _.
	•	Windows reserved names (e.g., CON, PRN) are wrapped with underscores to avoid conflicts.
	•	Length is capped (default 120 chars). If a filename already exists, a short hash suffix is added to avoid overwrites.

⸻

How it works (internals)
	•	Listing URL: https://www.nature.com/nature/articles?sort=PubDate[&year=YYYY]&page=N
	•	Parsing listings: Finds article blocks, extracts data-test="article.type" and the main link.
	•	Article fetch: Requests each matching URL; parses title from common meta tags or <h1>, then tries body containers such as div.c-article-body.
	•	Graceful fallbacks: If no body is found, it uses teaser/description; if still empty, writes "No content available.".
	•	HTTP session: Retries with backoff for transient errors (429/5xx) and a polite User-Agent.

⸻

Tips & Good Citizenship
	•	Start with small --pages and a larger --delay (e.g., 1.5–3.0).
	•	Avoid parallel runs against the same site.
	•	If you see HTTP 429 (rate limited), increase --delay or try later.
	•	Content behind paywalls or rendered dynamically may not yield full text; this scraper focuses on HTML paragraphs.

⸻

Troubleshooting
	•	[WARN] listing ... HTTP 429: You’re sending too many requests. Increase --delay, reduce --pages.
	•	[ERROR] ... RequestException: Temporary network issue. The session will retry but may still fail; run again later.
	•	Empty/short files: The article may be paywalled or structured differently; check the URL manually.
	•	Different types not matching: Remember --type is an exact match to Nature’s label.

⸻

Development notes
	•	Core entrypoint: main() with argparse.
	•	Key functions: build_session, sanitize_filename, extract_title, extract_teaser_or_body, parse_listing, scrape_nature.
	•	metadata.jsonl is opened in append mode, so repeated runs add lines. Delete it if you want a fresh index.

Running in a virtual environment

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt


⸻

FAQ

Q: Does this bypass paywalls?
A: No. It only parses publicly available HTML. Paywalled content will not be scraped.

Q: Can I scrape other Nature journals?
A: The base listing URL targets nature.com/nature/articles. You can adapt BASE_URL and the listing path, but CSS selectors may need updates.

Q: How do I change the user agent?
A: Edit build_session() and modify the User-Agent header string.

⸻

Contributing

Issues and PRs are welcome. Please keep changes small and add helpful log messages.

License

Choose a license that suits your project (e.g., MIT, Apache-2.0) and add a LICENSE file.
