#!/usr/bin/env python3
"""Scrape UNM/CSWR Archdiocese of Santa Fe Institutional Abuse Collection."""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.scrapers.santa_fe import SantaFeScraper


def main():
    parser = argparse.ArgumentParser(description="Scrape Santa Fe abuse archive")
    parser.add_argument("--output", default="data/raw/santa_fe", help="Output directory")
    parser.add_argument("--download-pdfs", action="store_true", help="Download PDF files")
    parser.add_argument("--max-size-mb", type=float, default=50, help="Max PDF size to download in MB (default 50)")
    args = parser.parse_args()

    scraper = SantaFeScraper(output_dir=args.output)

    try:
        stats = scraper.crawl_all()

        if args.download_pdfs:
            print(f"\n{'='*60}")
            print("Downloading PDFs...")
            print(f"{'='*60}")
            pdf_stats = scraper.download_pdfs(max_size_mb=args.max_size_mb)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
