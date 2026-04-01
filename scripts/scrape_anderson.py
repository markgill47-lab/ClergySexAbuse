#!/usr/bin/env python3
"""Scrape Anderson Advocates nationally — all states, all dioceses."""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.scrapers.anderson import AndersonScraper


def main():
    parser = argparse.ArgumentParser(description="Scrape Anderson Advocates clergy data")
    parser.add_argument("--output", default="data/raw/anderson", help="Output directory")
    parser.add_argument("--state", help="Scrape only a specific state (e.g., 'california')")
    parser.add_argument("--discover-only", action="store_true", help="Only discover states/dioceses, don't crawl profiles")
    parser.add_argument("--skip-pdfs", action="store_true", help="Skip PDF downloads (metadata only)")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between requests in seconds")
    args = parser.parse_args()

    scraper = AndersonScraper(output_dir=args.output)
    scraper.delay = args.delay

    try:
        # Discover states
        scraper.discover_states()

        if args.state:
            # Filter to specific state
            if args.state not in scraper.states:
                print(f"State '{args.state}' not found. Available: {list(scraper.states.keys())}")
                return
            scraper.states = {args.state: scraper.states[args.state]}
            print(f"\nFiltered to state: {args.state}")

        if args.discover_only:
            print("\nDiscovery complete. Use --state or no flag to crawl profiles.")
            return

        # Crawl all profiles
        stats = scraper.crawl_all()

        # Download PDFs
        if not args.skip_pdfs:
            print(f"\n{'='*60}")
            print("Downloading PDFs...")
            print(f"{'='*60}")
            pdf_stats = scraper.download_all_pdfs()

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
