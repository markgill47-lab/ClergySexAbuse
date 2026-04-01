"""Anderson Advocates national scraper.

Generalized from the MN-Clergy-Abuse project's 01_crawl_profiles.py.
Discovers all states and dioceses dynamically, then scrapes profiles,
PDFs, and YouTube video references.

Usage:
    from src.pipeline.scrapers.anderson import AndersonScraper
    scraper = AndersonScraper(output_dir="data/raw/anderson")
    scraper.discover_states()        # Find all state pages
    scraper.crawl_all()              # Crawl all profiles
    scraper.download_all_pdfs()      # Download PDFs
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.backend.config import SCRAPE_DELAY_SECONDS


BASE_URL = "https://www.andersonadvocates.com"

HEADERS = {
    "User-Agent": "ClergyAbuseResearch/1.0 (academic research)",
}

# Known state entry points from the Anderson site
# These follow the pattern /abused-in-{state}/ or /locations/abused-in-{state}/
KNOWN_STATE_PATHS = {
    "minnesota": "/abused-in-minnesota/minnesota-dioceses/",
    "california": "/abused-in-california/california-dioceses/",
    "arizona": "/abused-in-arizona/arizona-dioceses/",
    "colorado": "/abused-in-colorado/colorado-dioceses/",
    "hawaii": "/abused-in-hawaii/hawaii-dioceses/",
    "new-york": "/abused-in-new-york/new-york-dioceses/",
    "new-jersey": "/abused-in-new-jersey/new-jersey-dioceses/",
    "pennsylvania": "/abused-in-pennsylvania/pennsylvania-dioceses/",
    "wisconsin": "/locations/abused-in-wisconsin/",
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
PDF_TIMEOUT = 120
PDF_CHUNK_SIZE = 8192


class AndersonScraper:
    def __init__(self, output_dir: str | Path = "data/raw/anderson"):
        self.output_dir = Path(output_dir)
        self.profiles_dir = self.output_dir / "profiles"
        self.pdfs_dir = self.output_dir / "pdfs"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)

        self.client = httpx.Client(headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        self.states: dict[str, dict] = {}  # state_slug → {path, dioceses: {slug: url}}
        self.all_profiles: dict[str, dict] = {}  # profile_slug → profile data
        self.delay = SCRAPE_DELAY_SECONDS

    def _fetch(self, url: str, retries: int = MAX_RETRIES) -> str | None:
        """Fetch a URL with retry logic."""
        for attempt in range(retries):
            try:
                resp = self.client.get(url)
                resp.raise_for_status()
                time.sleep(self.delay)
                return resp.text
            except Exception as e:
                if attempt < retries - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  Retry {attempt + 1}/{retries} for {url} (waiting {wait}s): {e}")
                    time.sleep(wait)
                else:
                    print(f"  FAILED after {retries} attempts: {url} — {e}")
                    return None

    # --- State & Diocese Discovery ---

    def discover_states(self) -> dict:
        """Discover all state pages and their diocese sub-pages.

        First tries known paths, then attempts to discover additional states
        from the site's navigation.
        """
        print("Discovering Anderson Advocates state pages...")

        for state_slug, path in KNOWN_STATE_PATHS.items():
            url = BASE_URL + path
            print(f"  Checking {state_slug}...")
            html = self._fetch(url)
            if not html:
                print(f"    SKIP: Could not fetch {url}")
                continue

            dioceses = self._discover_dioceses(html, url)
            self.states[state_slug] = {
                "path": path,
                "url": url,
                "dioceses": dioceses,
            }
            print(f"    Found {len(dioceses)} diocese(s)")

        # Also try discovering from the main locations page
        self._discover_from_locations_page()

        # Save discovery results
        discovery_path = self.output_dir / "_states.json"
        with open(discovery_path, "w", encoding="utf-8") as f:
            json.dump(self.states, f, indent=2)

        total_dioceses = sum(len(s["dioceses"]) for s in self.states.values())
        print(f"\nDiscovered {len(self.states)} states, {total_dioceses} dioceses")
        return self.states

    def _discover_dioceses(self, html: str, base_url: str) -> dict[str, str]:
        """Extract diocese links from a state page."""
        soup = BeautifulSoup(html, "lxml")
        dioceses = {}

        # Look for links to diocese pages — they typically contain /dioceses/ or /accused/
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)

            # Diocese pages typically have patterns like:
            # /abused-in-california/california-dioceses/archdiocese-of-los-angeles/
            if "dioces" in href.lower() and text and len(text) > 3:
                full_url = urljoin(base_url, href)
                # Extract diocese slug from URL
                parts = [p for p in href.rstrip("/").split("/") if p]
                if parts:
                    slug = parts[-1]
                    if slug not in dioceses and slug not in ("dioceses", "minnesota-dioceses",
                            "california-dioceses", "arizona-dioceses", "colorado-dioceses",
                            "hawaii-dioceses", "new-york-dioceses", "new-jersey-dioceses",
                            "pennsylvania-dioceses"):
                        dioceses[slug] = full_url

        return dioceses

    def _discover_from_locations_page(self):
        """Try to find additional states from the main locations/practice areas page."""
        for path in ["/locations/", "/practice-areas/clergy-abuse/"]:
            html = self._fetch(BASE_URL + path)
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                match = re.search(r"/abused-in-([a-z-]+)/", href)
                if match:
                    state_slug = match.group(1)
                    if state_slug not in self.states:
                        print(f"  Discovered new state: {state_slug}")
                        full_url = urljoin(BASE_URL, href)
                        state_html = self._fetch(full_url)
                        if state_html:
                            dioceses = self._discover_dioceses(state_html, full_url)
                            self.states[state_slug] = {
                                "path": href,
                                "url": full_url,
                                "dioceses": dioceses,
                            }

    # --- Profile Crawling ---

    def _load_existing_profiles(self):
        """Load already-crawled profiles for resume support."""
        count = 0
        for profile_path in self.profiles_dir.glob("*.json"):
            if profile_path.name.startswith("_"):
                continue
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                slug = profile.get("slug", profile_path.stem)
                self.all_profiles[slug] = profile
                count += 1
            except (json.JSONDecodeError, KeyError):
                continue
        if count:
            print(f"  Loaded {count} existing profiles (resume mode)")

    def crawl_all(self) -> dict:
        """Crawl all profiles across all discovered states and dioceses."""
        if not self.states:
            print("No states discovered. Run discover_states() first.")
            return {}

        # Resume support: load already-crawled profiles
        self._load_existing_profiles()

        stats = {"states": 0, "dioceses": 0, "profiles": 0, "skipped": 0}

        for state_slug, state_info in self.states.items():
            print(f"\n{'='*60}")
            print(f"State: {state_slug}")
            print(f"{'='*60}")
            stats["states"] += 1

            for diocese_slug, diocese_url in state_info["dioceses"].items():
                print(f"\n  Diocese: {diocese_slug}")
                stats["dioceses"] += 1

                profile_links = self._scrape_diocese_index(diocese_url)
                print(f"    Found {len(profile_links)} profile links")

                for i, (name, url, image_url) in enumerate(profile_links):
                    slug = url.rstrip("/").split("/")[-1]

                    # Skip if already crawled (dedup across dioceses)
                    if slug in self.all_profiles:
                        # But track this diocese
                        if diocese_slug not in self.all_profiles[slug].get("all_dioceses", []):
                            self.all_profiles[slug]["all_dioceses"].append(diocese_slug)
                        stats["skipped"] += 1
                        continue

                    safe_name = name.encode("ascii", errors="replace").decode("ascii")
                    print(f"    [{i+1}/{len(profile_links)}] {safe_name}...")
                    profile = self._scrape_profile(url, slug, name, image_url, state_slug, diocese_slug)
                    if profile:
                        self.all_profiles[slug] = profile
                        # Save individual profile JSON
                        with open(self.profiles_dir / f"{slug}.json", "w", encoding="utf-8") as f:
                            json.dump(profile, f, indent=2, ensure_ascii=False)
                        stats["profiles"] += 1

        # Save master index
        self._save_index(stats)
        print(f"\n{'='*60}")
        print(f"COMPLETE: {stats['profiles']} profiles from {stats['dioceses']} dioceses in {stats['states']} states")
        return stats

    def _scrape_diocese_index(self, url: str) -> list[tuple[str, str, str | None]]:
        """Scrape a diocese index page for profile links.

        Returns list of (name, profile_url, image_url) tuples.
        """
        html = self._fetch(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        profiles = []

        # Anderson uses <h6> tags with <a> links to profiles
        for h6 in soup.find_all("h6"):
            link = h6.find("a", href=lambda h: h and "/accused/" in h)
            if not link:
                continue

            name = link.get_text(strip=True)
            profile_url = urljoin(url, link["href"])

            # Find portrait image in parent container
            image_url = None
            parent = h6.parent
            if parent:
                img = parent.find("img")
                if img and img.get("src"):
                    image_url = urljoin(url, img["src"])

            profiles.append((name, profile_url, image_url))

        return profiles

    def _scrape_profile(self, url: str, slug: str, name: str,
                        image_url: str | None, state_slug: str,
                        diocese_slug: str) -> dict | None:
        """Scrape an individual profile page."""
        html = self._fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n", strip=True)

        # Extract structured fields via regex
        title = self._extract_title(soup)
        ordination_date = self._regex_extract(text, r"[Oo]rdained[:\s]+(.+?)(?:\n|$)")
        date_of_birth = self._regex_extract(text, r"(?:DOB|Date of Birth|Born)[:\s]+(.+?)(?:\n|$)")
        current_address = self._regex_extract(text, r"(?:Current Address|Address)[:\s]+(.+?)(?:\n|$)")
        status = self._regex_extract(text, r"(?:Ministerial Status|Status)[:\s]+(.+?)(?:\n|$)")

        # Extract assignments (lines starting with year ranges)
        assignments = self._extract_assignments(soup)

        # Extract narrative paragraphs
        narrative = self._extract_narrative(soup)

        # Extract PDF links
        pdfs = self._extract_pdf_links(soup, url)

        # Extract YouTube videos (regex on raw HTML for lazy-loaded iframes)
        youtube_videos = self._extract_youtube(html)

        # Extract all images
        images = self._extract_images(soup, url)

        return {
            "slug": slug,
            "name": name,
            "url": url,
            "state": state_slug,
            "diocese": diocese_slug,
            "all_dioceses": [diocese_slug],
            "image_url": image_url,
            "title": title or name,
            "date_of_birth": date_of_birth,
            "ordination_date": ordination_date,
            "current_address": current_address,
            "status": status,
            "assignments": assignments,
            "narrative": narrative,
            "pdfs": pdfs,
            "youtube_videos": youtube_videos,
            "images": images,
        }

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        for tag in ["h1", "h2"]:
            el = soup.find(tag)
            if el:
                title = el.get_text(strip=True)
                # Strip common suffixes
                title = re.sub(r"\s*:\s*Accused of Child Sexual Abuse\s*$", "", title, flags=re.IGNORECASE)
                return title
        return None

    def _regex_extract(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_assignments(self, soup: BeautifulSoup) -> list[str]:
        assignments = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if re.match(r"\d{4}", text):
                assignments.append(text)
        return assignments

    def _extract_narrative(self, soup: BeautifulSoup) -> list[str]:
        paragraphs = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 30:
                paragraphs.append(text)
        return paragraphs

    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        pdfs = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                full_url = urljoin(base_url, href)
                if full_url not in seen:
                    seen.add(full_url)
                    filename = full_url.split("/")[-1]
                    pdfs.append({"url": full_url, "filename": filename, "title": a.get_text(strip=True) or filename})
        return pdfs

    def _extract_youtube(self, raw_html: str) -> list[dict]:
        """Extract YouTube video IDs from raw HTML (handles lazy-loaded iframes)."""
        ids = set()
        for pattern in [
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        ]:
            for match in re.finditer(pattern, raw_html):
                ids.add(match.group(1))

        return [
            {
                "video_id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "embed_url": f"https://www.youtube.com/embed/{vid}",
            }
            for vid in ids
        ]

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        images = []
        for img in soup.find_all("img", src=True):
            src = urljoin(base_url, img["src"])
            if "wp-content/uploads" in src:
                images.append({"url": src, "alt": img.get("alt", "")})
        return images

    # --- PDF Download ---

    def download_all_pdfs(self) -> dict:
        """Download all PDFs referenced in crawled profiles."""
        stats = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}
        manifest = {}

        for slug, profile in self.all_profiles.items():
            for pdf_info in profile.get("pdfs", []):
                stats["total"] += 1
                url = pdf_info["url"]
                filename = pdf_info["filename"]
                dest_dir = self.pdfs_dir / slug
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / filename

                if dest_path.exists() and dest_path.stat().st_size > 0:
                    stats["skipped"] += 1
                    manifest[url] = "skipped"
                    continue

                print(f"  Downloading: {slug}/{filename}...")
                success = self._download_file(url, dest_path)
                if success:
                    stats["downloaded"] += 1
                    manifest[url] = "downloaded"
                else:
                    stats["failed"] += 1
                    manifest[url] = "failed"

        # Save manifest
        with open(self.pdfs_dir / "_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\nPDFs: {stats['downloaded']} downloaded, {stats['skipped']} skipped, {stats['failed']} failed")
        return stats

    def _download_file(self, url: str, dest: Path) -> bool:
        """Download a file with streaming and retry."""
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
                    dest.unlink()  # Clean up partial download
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** (attempt + 1))
                else:
                    print(f"    FAILED: {e}")
                    return False
        return False

    # --- Index Management ---

    def _save_index(self, stats: dict):
        """Save master index of all crawled profiles."""
        from datetime import datetime

        # Build diocese breakdown
        diocese_counts = {}
        for profile in self.all_profiles.values():
            for d in profile.get("all_dioceses", []):
                diocese_counts[d] = diocese_counts.get(d, 0) + 1

        # Build state breakdown
        state_counts = {}
        for profile in self.all_profiles.values():
            state = profile.get("state", "unknown")
            state_counts[state] = state_counts.get(state, 0) + 1

        index = {
            "crawl_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_profiles": len(self.all_profiles),
            "total_with_pdfs": sum(1 for p in self.all_profiles.values() if p.get("pdfs")),
            "total_pdfs": sum(len(p.get("pdfs", [])) for p in self.all_profiles.values()),
            "total_with_videos": sum(1 for p in self.all_profiles.values() if p.get("youtube_videos")),
            "total_videos": sum(len(p.get("youtube_videos", [])) for p in self.all_profiles.values()),
            "states": state_counts,
            "dioceses": diocese_counts,
            "profiles": [
                {
                    "slug": slug,
                    "name": p["name"],
                    "url": p["url"],
                    "state": p.get("state"),
                    "all_dioceses": p.get("all_dioceses", []),
                    "pdf_count": len(p.get("pdfs", [])),
                    "video_count": len(p.get("youtube_videos", [])),
                }
                for slug, p in sorted(self.all_profiles.items())
            ],
        }

        with open(self.output_dir / "_index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def close(self):
        self.client.close()
