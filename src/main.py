import os
import time
import json
import re
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional

# ============================================
# CONFIG
# ============================================
BASE_URL = "https://books.toscrape.com/"
CATALOGUE_URL = BASE_URL + "catalogue/page-{}.html"
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/Kalaivaniparthi/scraper)"
TIMEOUT = 5
DELAY = 0.5

HEADERS = {"User-Agent": USER_AGENT}

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================
# SCHEMA
# ============================================
class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str


# ============================================
# FETCH
# ============================================
def fetch(url, cache_path, max_retries=1):
    """Fetch with politeness, caching, and one retry on failure."""
    if os.path.exists(cache_path):
        print(f"CACHE HIT  {url}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    attempt = 0
    while attempt <= max_retries:
        try:
            print(f"FETCH      {url} (attempt {attempt + 1})")
            time.sleep(DELAY)
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            if response.status_code == 200:
                html = response.text
                print(f"           status=200 size={len(html)} bytes")
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html)
                return html

            if response.status_code in (404, 403):
                raise Exception(f"Failed fetch: {response.status_code}")

            if 500 <= response.status_code < 600 and attempt < max_retries:
                attempt += 1
                time.sleep(2)
                continue

            raise Exception(f"Failed fetch: {response.status_code}")
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                attempt += 1
                time.sleep(2)
                continue
            raise


# ============================================
# DISCOVERY
# ============================================
def get_book_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for h3 in soup.select("h3"):
        a = h3.find("a")
        if a and a.get("href"):
            links.append(urljoin(page_url, a["href"]))
    return links


def get_next_page(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    next_btn = soup.select_one("li.next a")
    if next_btn and next_btn.get("href"):
        return urljoin(page_url, next_btn["href"])
    return None


# ============================================
# EXTRACT
# ============================================
def extract_raw(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.product_main")

    title = product.select_one("h1").get_text(strip=True) if product else None

    price_el = product.select_one("p.price_color") if product else None
    price_text = price_el.get_text(strip=True) if price_el else None

    avail_el = product.select_one("p.instock.availability") if product else None
    availability_text = avail_el.get_text(strip=True) if avail_el else None

    rating_el = product.select_one("p.star-rating") if product else None
    rating_text = None
    if rating_el:
        for c in rating_el.get("class", []):
            if c != "star-rating":
                rating_text = c
                break

    desc_el = soup.select_one("div#product_description ~ p")
    description = desc_el.get_text(strip=True) if desc_el else None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================
# NORMALIZE
# ============================================
def normalize(raw):
    """Convert raw fields into clean fields."""
    m = re.search(r"[\d.]+", raw["price_text"] or "")
    return {
        "title": raw["title"],
        "product_url": raw["product_url"],
        "price_gbp": float(m.group()) if m else None,
        "availability_text": raw["availability_text"],
        "rating_text": raw["rating_text"],
        "description": raw["description"],
        "source_page": raw["source_page"],
        "fetched_at": raw["fetched_at"],
    }


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    start_time = time.time()

    # ---- Discover all catalogue pages ----
    all_urls = []
    catalogue_pages = 0
    next_url = CATALOGUE_URL.format(1)
    page_num = 1

    while next_url and page_num <= 3:
        cache_path = f"{CACHE_DIR}/catalogue-page-{page_num}.html"
        html = fetch(next_url, cache_path)
        catalogue_pages += 1

        for book_url in get_book_links(html, next_url):
            if book_url not in all_urls:
                all_urls.append(book_url)

        next_url = get_next_page(html, next_url)
        page_num += 1

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(all_urls)}")

    # ---- Add ONE fake URL to test failure handling ----
    test_urls = all_urls + [
        "https://books.toscrape.com/catalogue/does-not-exist/index.html"
    ]

    # ---- Extract each book ----
    raw_records = []
    failed_pages = []
    pages_fetched = 0
    cache_hits = 0

    for i, url in enumerate(test_urls, start=1):
        cache_path = f"{CACHE_DIR}/book-{i}.html"
        if os.path.exists(cache_path):
            cache_hits += 1
        else:
            pages_fetched += 1

        try:
            html = fetch(url, cache_path)
            raw_records.append(extract_raw(html, url, CATALOGUE_URL.format(1)))
        except Exception as e:
            print(f"FAILED {url}: {e}")
            failed_pages.append({"url": url, "error": str(e)})

    print(f"detail_pages={len(raw_records)}")

    # ---- Normalize + Validate ----
    valid_records = []
    invalid_records = []
    seen_urls = set()

    for raw in raw_records:
        try:
            clean = normalize(raw)
            record = BookRecord(**clean)

            # Deduplicate by canonical URL
            url_str = str(record.product_url)
            if url_str in seen_urls:
                continue
            seen_urls.add(url_str)

            valid_records.append(record.model_dump(mode="json"))
        except ValidationError as e:
            invalid_records.append({"raw": raw, "error": str(e)})
        except Exception as e:
            invalid_records.append({"raw": raw, "error": str(e)})

    # ---- Store ----
    with open(f"{OUTPUT_DIR}/books.json", "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(f"{OUTPUT_DIR}/errors.json", "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2, ensure_ascii=False)

    # ---- Run report ----
    report = {
        "start_time": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - start_time, 2),
        "catalogue_pages": catalogue_pages,
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_pages": len(failed_pages),
        "failures": failed_pages,
    }

    with open(f"{OUTPUT_DIR}/run-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
