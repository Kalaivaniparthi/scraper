# Polite Scraper

A polite web scraper that downloads the first 3 catalogue pages from [Books to Scrape](https://books.toscrape.com/), visits all 60 book pages, and turns messy HTML into clean, validated JSON.

---

## Target Classification

- **Site:** https://books.toscrape.com/
- **Why this site:** Public sandbox built specifically for scraping practice
- **Scope:** First 3 catalogue pages only (60 books total)
- **Data collected:** title, product_url, price_gbp, availability_text, rating_text, description, source_page, fetched_at
- **Ethics:** Use official APIs when they exist. Never bypass logins, paywalls, or blocks. Collect only what is needed.

### Robots.txt

404 Not Found — no robots file exists. A missing file is not permission, just a missing file.

---

## Politeness Rules

- **User-Agent:** `FlyRankInternshipA9/1.0 (+https://github.com/Kalaivaniparthi/scraper)`
- **Timeout:** 5 seconds per request
- **Delay:** 0.5 seconds between real requests
- **Cache:** All HTML saved to `cache/` — never re-fetch during development
- **Retries:** One retry on 5xx errors and timeouts. Never retry 404 or 403.

---

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Run

```bash
python src/main.py
```

---

## Output

| File | What's inside |
|------|---------------|
| `output/books.json` | 60 validated records |
| `output/errors.json` | Records that failed schema validation |
| `output/run-report.json` | Honest summary of the last run |

---

## Record Schema

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-09-27T..."
}
```

---

## Sample Run Report

```json
{
  "start_time": "2026-09-27T08:00:00+00:00",
  "duration_seconds": 1.5,
  "catalogue_pages": 3,
  "pages_fetched": 0,
  "cache_hits": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failures": [
    {
      "url": "https://books.toscrape.com/catalogue/does-not-exist/index.html",
      "error": "Failed fetch: 404"
    }
  ]
}
```

---

## Why No Browser?

The data is already in the HTML the server sends. A headless browser would only add cost (memory, time, complexity) without any benefit. Scraping the HTML directly is faster and lighter.

---

## Ethics

- Use an official API when one exists.
- Never bypass logins, paywalls, or blocks.
- Collect only what you need.

---

## One Honest Limitation

The scraper does **not** handle paginated book listings beyond the 3 catalogue pages hardcoded in this assignment. To scrape the full catalogue (50 pages), change the `page_num <= 3` condition in `src/main.py`.

---

## Author

**Kalaivani Parthi** — FlyRank Backend AI Engineering Internship, Week 5, Assignment A9
