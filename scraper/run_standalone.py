"""CLI entrypoint for running the refactored MahaRERA scraper standalone.

Usage:
    python scraper/run_standalone.py --start-page 1 --end-page 2 --district "Raigarh" --district-code "520"
"""
import argparse
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger
from scraper.core.worker import ScraperWorker


def main():
    parser = argparse.ArgumentParser(description="MahaRERA Standalone Scraper")
    parser.add_argument("--start-page", type=int, default=1, help="Start page number (default: 1)")
    parser.add_argument("--end-page", type=int, default=2, help="End page number exclusive (default: 2)")
    parser.add_argument("--district", type=str, default="Raigarh", help="District name (default: Raigarh)")
    parser.add_argument("--district-code", type=str, default="520", help="District code (default: 520)")
    parser.add_argument("--workers", type=int, default=4, help="Max worker threads (default: 4)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless Chrome")
    parser.add_argument("--output", type=str, default="Raigarh_output_NEW.csv", help="Output CSV path")

    args = parser.parse_args()

    config = ScraperConfig(
        start_page=args.start_page,
        end_page=args.end_page,
        district_name=args.district,
        district_code=args.district_code,
        max_workers=args.workers,
        headless=args.headless,
        output_csv=args.output,
    )
    logger = ScraperLogger(log_file=config.run_log_file)
    logger.info(f"Starting standalone scrape for {config.district_name} (pages {config.start_page} to {config.end_page})...")

    worker = ScraperWorker(config=config, logger=logger)
    df = worker.run_scrape()
    logger.info(f"Done. Scraped {len(df)} projects.")


if __name__ == "__main__":
    main()

