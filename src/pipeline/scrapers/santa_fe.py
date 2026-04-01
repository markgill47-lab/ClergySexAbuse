"""UNM/CSWR Archdiocese of Santa Fe Institutional Abuse Collection scraper.

Scrapes metadata and optionally downloads PDFs from the UNM Digital Repository.
The collection contains personnel files, depositions, review board records,
and legal documents from the $121.5M settlement.

Usage:
    from src.pipeline.scrapers.santa_fe import SantaFeScraper
    scraper = SantaFeScraper(output_dir="data/raw/santa_fe")
    scraper.crawl_all()                    # Metadata only
    scraper.download_pdfs(max_size_mb=50)  # Download PDFs under 50MB
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.backend.config import SCRAPE_DELAY_SECONDS


BASE_URL = "https://digitalrepository.unm.edu"

HEADERS = {
    "User-Agent": "ClergyAbuseResearch/1.0 (academic research)",
}

# All known sub-collections with their URL contexts
COLLECTIONS = {
    "asf_personnelfiles": {
        "name": "Personnel Files",
        "series": "archdiocese",
        "context": "cswr_asf_personnelfiles",
        "doc_type": "personnel_file",
    },
    "asf_depositions": {
        "name": "Depositions",
        "series": "archdiocese",
        "context": "cswr_asf_depositions",
        "doc_type": "deposition",
    },
    "asf_permanentreviewboard": {
        "name": "Permanent Review Board",
        "series": "archdiocese",
        "context": "cswr_asf_permanentreviewboard",
        "doc_type": "review_board",
    },
    "asf_personnelboard": {
        "name": "Personnel Board",
        "series": "archdiocese",
        "context": "cswr_asf_personnelboard",
        "doc_type": "personnel_board",
    },
    "asf_policiesandsurveys": {
        "name": "Policies and Surveys",
        "series": "archdiocese",
        "context": "cswr_asf_policiesandsurveys",
        "doc_type": "policy",
    },
    "hm_depositions": {
        "name": "Hall & Monagle Depositions",
        "series": "hall_monagle",
        "context": "cswr_hm_depositions",
        "doc_type": "deposition",
    },
    "hm_otherfiles": {
        "name": "Hall & Monagle Other Files",
        "series": "hall_monagle",
        "context": "cswr_hm_otherfiles",
        "doc_type": "legal_filing",
    },
    "hm_personneltypefiles": {
        "name": "Hall & Monagle Personnel-Type Files",
        "series": "hall_monagle",
        "context": "cswr_hm_personneltypefiles",
        "doc_type": "personnel_file",
    },
    "hm_proofsofclaims": {
        "name": "Hall & Monagle Proofs of Claims",
        "series": "hall_monagle",
        "context": "cswr_hm_proofsofclaims",
        "doc_type": "proof_of_claim",
    },
    "hm_timelines": {
        "name": "Hall & Monagle Timelines",
        "series": "hall_monagle",
        "context": "cswr_hm_timelines",
        "doc_type": "timeline",
    },
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
PDF_TIMEOUT = 300  # Large files
PDF_CHUNK_SIZE = 65536  # 64KB chunks for large PDFs


class SantaFeScraper:
    def __init__(self, output_dir: str | Path = "data/raw/santa_fe"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir = self.output_dir / "pdfs"
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)

        self.client = httpx.Client(headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        self.all_items: list[dict] = []
        self.delay = SCRAPE_DELAY_SECONDS

    def _fetch(self, url: str, retries: int = MAX_RETRIES) -> str | None:
        for attempt in range(retries):
            try:
                resp = self.client.get(url)
                resp.raise_for_status()
                time.sleep(self.delay)
                return resp.text
            except Exception as e:
                if attempt < retries - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  Retry {attempt + 1}/{retries} for {url} (waiting {wait}s)")
                    time.sleep(wait)
                else:
                    print(f"  FAILED: {url} - {e}")
                    return None

    def crawl_all(self) -> dict:
        """Crawl all sub-collections and extract metadata for every item."""
        stats = {"collections": 0, "items": 0, "failed_collections": 0}

        for key, config in COLLECTIONS.items():
            print(f"\n--- {config['name']} ---")
            context = config["context"]
            index_url = f"{BASE_URL}/{context}/"

            items = self._crawl_collection(index_url, context, config)
            if items is None:
                stats["failed_collections"] += 1
                print(f"  SKIP: Could not access {index_url}")
                continue

            self.all_items.extend(items)
            stats["collections"] += 1
            stats["items"] += len(items)
            print(f"  Found {len(items)} items")

        # Save all metadata
        self._save_index(stats)
        print(f"\nCOMPLETE: {stats['items']} items from {stats['collections']} collections")
        return stats

    def _crawl_collection(self, index_url: str, context: str, config: dict) -> list[dict] | None:
        """Crawl all pages of a collection index, extracting item links."""
        items = []
        page = 1

        while True:
            if page == 1:
                url = index_url
            else:
                url = f"{index_url}index.{page}.html"

            html = self._fetch(url)
            if not html:
                if page == 1:
                    return None
                break  # No more pages

            soup = BeautifulSoup(html, "lxml")
            page_items = self._extract_items_from_index(soup, context, config)

            if not page_items:
                break

            items.extend(page_items)
            print(f"  Page {page}: {len(page_items)} items")

            # Check for next page
            next_link = soup.find("a", string=str(page + 1))
            if not next_link:
                break
            page += 1

        # Fetch detailed metadata for each item
        for i, item in enumerate(items):
            if item.get("item_url"):
                safe_title = item["title"].encode("ascii", errors="replace").decode("ascii")
                print(f"  [{i+1}/{len(items)}] {safe_title}")
                detail = self._fetch_item_detail(item["item_url"], context)
                if detail:
                    item.update(detail)

        return items

    def _extract_items_from_index(self, soup: BeautifulSoup, context: str, config: dict) -> list[dict]:
        """Extract item links and basic metadata from a collection index page."""
        items = []

        # The repository uses <p class="article-listing"> or similar patterns
        # Look for links that point to individual items
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Match pattern: /context/NUMBER/ or /context/NUMBER
            pattern = f"/{context}/(\\d+)"
            match = re.search(pattern, href)
            if not match:
                continue

            item_num = match.group(1)
            title = a.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Avoid duplicate links (navigation, etc.)
            full_url = urljoin(BASE_URL, href)
            if any(it["item_url"] == full_url for it in items):
                continue

            # Try to extract file size from nearby text
            file_size = None
            parent = a.parent
            if parent:
                parent_text = parent.get_text()
                size_match = re.search(r"(\d+(?:\.\d+)?)\s*(MB|KB|GB)", parent_text)
                if size_match:
                    size_val = float(size_match.group(1))
                    unit = size_match.group(2)
                    if unit == "KB":
                        file_size = size_val / 1024
                    elif unit == "GB":
                        file_size = size_val * 1024
                    else:
                        file_size = size_val  # MB

            items.append({
                "item_num": int(item_num),
                "title": title,
                "item_url": full_url,
                "context": context,
                "collection": config["name"],
                "series": config["series"],
                "doc_type": config["doc_type"],
                "file_size_mb": file_size,
                "pdf_url": None,  # Filled in by detail fetch
            })

        return items

    def _fetch_item_detail(self, url: str, context: str) -> dict | None:
        """Fetch an individual item page and extract detailed metadata."""
        html = self._fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        detail = {}

        # Extract metadata from the page
        # Title
        title_el = soup.find("meta", {"name": "DC.Title"}) or soup.find("meta", {"name": "bepress_citation_title"})
        if title_el:
            detail["full_title"] = title_el.get("content", "")

        # Author/Creator
        author_el = soup.find("meta", {"name": "DC.Creator"}) or soup.find("meta", {"name": "bepress_citation_author"})
        if author_el:
            detail["creator"] = author_el.get("content", "")

        # Date
        date_el = soup.find("meta", {"name": "DC.Date"}) or soup.find("meta", {"name": "bepress_citation_date"})
        if date_el:
            detail["date"] = date_el.get("content", "")

        # Description
        desc_el = soup.find("meta", {"name": "DC.Description"})
        if desc_el:
            detail["description"] = desc_el.get("content", "")

        # PDF URL
        pdf_el = soup.find("meta", {"name": "bepress_citation_pdf_url"})
        if pdf_el:
            detail["pdf_url"] = pdf_el.get("content", "")
        else:
            # Fallback: construct from article number
            article_match = re.search(r"article=(\d+)", str(soup))
            if article_match:
                detail["pdf_url"] = f"{BASE_URL}/cgi/viewcontent.cgi?article={article_match.group(1)}&context={context}"

        # Extract clergy name from title
        clergy_name = self._extract_clergy_name(detail.get("full_title", "") or "")
        if clergy_name:
            detail["clergy_name"] = clergy_name

        return detail

    def _extract_clergy_name(self, title: str) -> str | None:
        """Extract clergy name from document titles like 'Personnel File of Fr. John Smith'."""
        # Strip trailing date patterns first: "2015", "2014.05", "1994.01.12"
        cleaned = re.sub(r"\s+\d{4}(?:\.\d{2}(?:\.\d{2})?)?$", "", title.strip())
        # Also strip trailing comma
        cleaned = cleaned.rstrip(",").strip()

        patterns = [
            r"Personnel File of (.+)",
            r"Deposition of (.+)",
            r"Timeline[:\s]+(.+)",
            r"Proof of Claim[:\s]+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up prefixes for consistency
                name = re.sub(r"^(Fr\.|Msgr\.|Br\.|Dn\.|Archbishop|Abp\.|Bishop)\s+", "", name)
                return name
        return None

    def download_pdfs(self, max_size_mb: float = 100) -> dict:
        """Download PDFs for all crawled items, optionally filtering by size.

        Args:
            max_size_mb: Skip PDFs larger than this (default 100MB).
                         Set to 0 to download everything.
        """
        stats = {"total": 0, "downloaded": 0, "skipped_size": 0, "skipped_exists": 0, "failed": 0}

        for item in self.all_items:
            pdf_url = item.get("pdf_url")
            if not pdf_url:
                continue

            stats["total"] += 1

            # Check size limit
            if max_size_mb > 0 and item.get("file_size_mb") and item["file_size_mb"] > max_size_mb:
                stats["skipped_size"] += 1
                continue

            # Build filename
            slug = re.sub(r"[^a-z0-9]+", "-", item["title"].lower()).strip("-")[:80]
            dest_dir = self.pdfs_dir / item["context"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / f"{slug}.pdf"

            if dest_path.exists() and dest_path.stat().st_size > 0:
                stats["skipped_exists"] += 1
                continue

            safe_title = item["title"].encode("ascii", errors="replace").decode("ascii")
            size_str = f" ({item['file_size_mb']:.1f} MB)" if item.get("file_size_mb") else ""
            print(f"  Downloading: {safe_title}{size_str}...")

            success = self._download_file(pdf_url, dest_path)
            if success:
                stats["downloaded"] += 1
                item["local_path"] = str(dest_path)
            else:
                stats["failed"] += 1

        # Update index with local paths
        self._save_index({})

        print(f"\nPDFs: {stats['downloaded']} downloaded, {stats['skipped_exists']} existed, "
              f"{stats['skipped_size']} too large, {stats['failed']} failed")
        return stats

    def _download_file(self, url: str, dest: Path) -> bool:
        for attempt in range(MAX_RETRIES):
            try:
                with self.client.stream("GET", url, timeout=PDF_TIMEOUT) as resp:
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(PDF_CHUNK_SIZE):
                            f.write(chunk)
                time.sleep(self.delay)
                return True
            except Exception as e:
                if dest.exists():
                    dest.unlink()
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** (attempt + 1))
                else:
                    print(f"    FAILED: {e}")
                    return False
        return False

    def _save_index(self, stats: dict):
        from datetime import datetime

        # Aggregate by collection
        collection_counts = {}
        for item in self.all_items:
            col = item.get("collection", "unknown")
            collection_counts[col] = collection_counts.get(col, 0) + 1

        # Aggregate by clergy name
        clergy_names = set()
        for item in self.all_items:
            name = item.get("clergy_name")
            if name:
                clergy_names.add(name)

        index = {
            "crawl_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "UNM/CSWR Archdiocese of Santa Fe Institutional Abuse Collection",
            "total_items": len(self.all_items),
            "unique_clergy_names": len(clergy_names),
            "clergy_names": sorted(clergy_names),
            "collections": collection_counts,
            "items": self.all_items,
        }

        with open(self.output_dir / "_index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def close(self):
        self.client.close()
