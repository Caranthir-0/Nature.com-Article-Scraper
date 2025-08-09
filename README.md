Nature Article Scraper

A robust, polite web scraper for recent nature.com listings that saves article teasers/bodies to text files and writes rich metadata to metadata.jsonl.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-blue" />
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green" />
  <img alt="Status" src="https://img.shields.io/badge/status-active-success" />
</p>


Highlights
	•	Resilient parsing of titles and content across several Nature layouts (meta tags, H1 fallbacks, body selectors, teaser fallbacks).
	•	Safe filenames for Windows/macOS/Linux.
	•	Retry with backoff and a polite default delay between requests.
	•	JSON Lines metadata for easy downstream analysis.

How it works

The script walks Nature listing pages (sorted by publication date), filters by year and article type (e.g., News), fetches each matching article, extracts the best-available title and text (body > teaser > meta description), sanitizes a filename, and saves:
	•	<outdir>/Page_<N>/<sanitized-title>.txt — the article text (or a brief fallback if paywalled)
	•	<outdir>/metadata.jsonl — one JSON object per line with fields like title, url, file, page, published, type, listed_type

Installation

# Clone the repo
git clone https://github.com/Caranthir-0/nature-article-scraper.git
cd nature-article-scraper

# (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

requirements.txt (provided in repo):

beautifulsoup4>=4.12
requests>=2.31

Quickstart

# Scrape 2 listing pages of all types for 2025, write to ./output
python scrape_nature.py --pages 2 --year 2025 --out output

# Scrape 5 listing pages, only items with type exactly "News", 2024
python scrape_nature.py --pages 5 --type "News" --year 2024 --out output_news_2024

# Be extra polite with a longer delay (in seconds)
python scrape_nature.py --pages 3 --delay 1.5

Arguments

Flag	Type	Required	Default	Description
--pages	int	Yes	—	Number of listing pages to scan
--type	str	No	""	Exact article type to match (e.g., News, Editorial)
--year	int	No	None	Filter by publication year
--out	str	No	output	Output directory
--delay	float	No	0.8	Delay between requests (seconds)

Output structure

output/
├─ metadata.jsonl
├─ Page_1/
│  ├─ A_safe_sanitized_title.txt
│  └─ Another_title.txt
└─ Page_2/
   └─ ...

metadata.jsonl example line:

{"title": "Quantum widgets beat classical...", "url": "https://www.nature.com/articles/xxxx", "file": "Page_1/Quantum_widgets_beat_classical.txt", "page": 1, "published": "2025-02-14", "type": "News", "listed_type": "News"}

Responsible use & scraping etiquette
	•	Respect the Terms of Use and robots.txt of target sites.
	•	Keep a sensible --delay (default is polite); do not hammer servers.
	•	Identify your scraper properly (customize the User-Agent string in build_session()).
	•	This tool is for personal/educational use; do not republish paywalled content.

Troubleshooting
	•	Empty text files: Some articles are paywalled/JS-rendered. The scraper will save a teaser/meta description; check metadata.jsonl and the debug logs.
	•	Weird filenames: We sanitize aggressively for cross-platform safety; see sanitize_filename().
	•	Few or no matches: Ensure the --type matches exactly what Nature lists (e.g., News, Editorial, Research Highlight). Try running without --type to inspect listed_type values in metadata.jsonl.

Development
	•	Python formatting: ruff / black (optional).
	•	Lint: ruff (optional).
	•	Tests (optional): add unit tests for sanitize_filename, parse_listing, and parsing helpers using cached HTML fixtures.

Suggested project structure

.
├─ scrape_nature.py
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ LICENSE
├─ examples/
│  └─ sample_metadata.jsonl
└─ tests/ (optional)

.gitignore (excerpt)

.venv/
__pycache__/
*.pyc
output/
*.log
.DS_Store

Roadmap
	•	Optional caching layer (e.g., requests-cache).
	•	Parallel fetch with rate limiting.
	•	Export to CSV/Parquet.
	•	Minimal HTML->Markdown conversion for cleaner text.

License

This project is licensed under the MIT License. See LICENSE for details.

Acknowledgements
	•	Nature page structure and components change over time; selectors here are best-effort and may need periodic updates.
