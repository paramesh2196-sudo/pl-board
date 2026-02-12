import traceback
from sqlalchemy.orm import Session
from models import JobListing
from scrapers.jobspy_scraper import JobSpyScraper
from scrapers.timesjobs_scraper import TimesJobsScraper
from scrapers.freshersworld_scraper import FreshersworldScraper
from scrapers.internshala_scraper import IntershalaScraper
from datetime import datetime

# List of ALL real scrapers
SCRAPERS = [
    ("JobSpy (Indeed/LinkedIn/Naukri/Google/Glassdoor)", JobSpyScraper()),
    ("TimesJobs", TimesJobsScraper()),
    ("Freshersworld", FreshersworldScraper()),
    ("Internshala", IntershalaScraper()),
]

CITIES = ["Bangalore", "Hyderabad", "Chennai", "Kolkata", "Mumbai", "Pune", "Gurgaon"]


def run_scrapers(db: Session):
    """Run all scrapers for all cities and save results to the database."""
    print(f"\n{'='*60}")
    print(f"Starting scheduled scrape at {datetime.now()}")
    print(f"Cities: {', '.join(CITIES)}")
    print(f"{'='*60}\n")

    total_new = 0
    total_skipped = 0

    for city in CITIES:
        print(f"\n--- Scraping {city} ---")
        for scraper_name, scraper in SCRAPERS:
            try:
                print(f"  Running {scraper_name}...")
                jobs = scraper.scrape(city)
                new_count = 0
                skip_count = 0

                for job_data in jobs:
                    try:
                        # Check if job already exists by URL
                        existing = db.query(JobListing).filter(
                            JobListing.url == job_data["url"]
                        ).first()

                        if not existing:
                            job = JobListing(**job_data)
                            db.add(job)
                            new_count += 1
                        else:
                            skip_count += 1
                    except Exception as e:
                        print(f"    Error saving job: {e}")
                        continue

                db.commit()
                total_new += new_count
                total_skipped += skip_count
                print(f"  ✓ {scraper_name}: {new_count} new, {skip_count} duplicates skipped")

            except Exception as e:
                print(f"  ✗ Error with {scraper_name} for {city}: {e}")
                traceback.print_exc()
                db.rollback()

    print(f"\n{'='*60}")
    print(f"Scrape finished at {datetime.now()}")
    print(f"Total new jobs added: {total_new}")
    print(f"Total duplicates skipped: {total_skipped}")
    print(f"{'='*60}\n")
