"""
Freshersworld.com scraper using BeautifulSoup.
Based on the proven approach from DepthStrider-x/fresher_world repo.
Uses correct CSS selectors, session-based requests, retry logic, and pagination.
"""
import re
import time
import random
import traceback
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from scrapers.jobspy_scraper import detect_technologies, detect_domain, is_walkin, normalize_city


def safe_text(parent, tag, class_name):
    """Safely extract text from a tag."""
    try:
        element = parent.find(tag, class_=class_name)
        return element.get_text(strip=True) if element else None
    except Exception:
        return None


def safe_attr(parent, tag, class_name, attr):
    """Safely extract an attribute from a tag."""
    try:
        element = parent.find(tag, class_=class_name)
        return element.get(attr) if element else None
    except Exception:
        return None


class FreshersworldScraper(BaseScraper):
    """Scrapes freshersworld.com for fresher/walk-in jobs using proven selectors."""

    BASE_URL = "https://www.freshersworld.com"
    LIMIT = 20
    MAX_PAGES = 3  # pages per category URL to keep scrape time reasonable

    # Working category URLs discovered from the site (format: slug/id)
    CATEGORY_URLS = [
        "/python-jobs/3535127",
        "/be-btech-jobs-vacancies/666616",
        "/bca-jobs-vacancies/666614",
        "/it-software-jobs-vacancies/1111010",
        "/bpo-jobs/3535036",
        "/data-entry-back-office-jobs-vacancies/1111006",
        "/bsc-jobs-vacancies/666620",
        "/bcom-jobs-vacancies/666606",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.freshersworld.com/",
        })

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic (3 attempts)."""
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                print(f"    [Freshersworld] Attempt {attempt + 1} failed for {url}: {e}")
                time.sleep(2)
        print(f"    [Freshersworld] Failed after 3 attempts: {url}")
        return None

    def _parse_jobs(self, html: str, target_city: str) -> List[Dict]:
        """Parse job listings from HTML using proven selectors from DepthStrider-x repo."""
        jobs = []
        if not html:
            return jobs

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return jobs

        # Primary selector — exact class from the working repo
        job_cards = soup.find_all(
            "div",
            class_="col-md-12 col-lg-12 col-xs-12 padding-none job-container jobs-on-hover top_space"
        )
        # Fallback selectors
        if not job_cards:
            job_cards = soup.find_all("div", class_="job-container")
        if not job_cards:
            job_cards = soup.find_all("div", class_="latest_jobs_in_wrapper")

        dates = soup.find_all("div", class_="text-ago")

        for i, card in enumerate(job_cards):
            try:
                # Title — primary selector from working repo
                title = safe_text(card, "span", "wrap-title seo_title")
                if not title:
                    link = card.find("a")
                    title = (link.get("title", "") or link.text.strip()) if link else ""
                if not title:
                    continue

                # Company — primary selector from working repo
                company = safe_text(
                    card, "h3",
                    "latest-jobs-title font-16 margin-none inline-block company-name"
                )
                if not company:
                    tag = card.find("span", class_="job-company") or card.find("h3")
                    company = tag.text.strip() if tag else "Unknown"

                # Location
                location_text = safe_text(card, "a", "bold_font")
                if not location_text:
                    loc_tag = card.find("span", class_="job-location") or card.find("span", {"itemprop": "addressLocality"})
                    location_text = loc_tag.text.strip() if loc_tag else target_city

                # Experience
                experience = safe_text(card, "span", "experience job-details-span")
                if not experience:
                    exp_tag = card.find("span", class_="job-experience")
                    experience = exp_tag.text.strip() if exp_tag else "Fresher"

                # Salary
                salary_text = safe_text(
                    card, "span",
                    "qualifications display-block modal-open pull-left job-details-span"
                )
                min_salary = None
                max_salary = None
                if salary_text:
                    nums = re.findall(r'[\d,.]+', salary_text.replace(",", ""))
                    if len(nums) >= 2:
                        try:
                            min_salary = float(nums[0])
                            max_salary = float(nums[1])
                        except (ValueError, IndexError):
                            pass

                # Description
                description = safe_text(card, "span", "desc") or ""

                # Job link — check job_display_url attribute first (from working repo)
                job_link = card.get("job_display_url")
                if not job_link:
                    link_tag = card.find("a")
                    if link_tag:
                        href = link_tag.get("href", "")
                        job_link = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                if not job_link:
                    continue

                # Post date from companion date divs
                post_date_text = ""
                if i < len(dates):
                    post_date_text = safe_text(dates[i], "span", "ago-text") or ""

                date_posted = date.today()
                if post_date_text:
                    text_lower = post_date_text.lower()
                    if "today" in text_lower or "just" in text_lower or "hour" in text_lower:
                        date_posted = date.today()
                    elif "yesterday" in text_lower or "1 day" in text_lower:
                        date_posted = date.today() - timedelta(days=1)
                    else:
                        days_match = re.search(r'(\d+)\s*day', text_lower)
                        if days_match:
                            days_ago = int(days_match.group(1))
                            date_posted = date.today() - timedelta(days=days_ago)
                            if days_ago > 14:
                                continue  # Skip old postings

                full_text = f"{title} {description}"
                city_name = normalize_city(location_text) or target_city

                jobs.append({
                    "title": title,
                    "company": company or "Unknown",
                    "city": city_name,
                    "state": None,
                    "country": "India",
                    "location_full": location_text,
                    "description": description[:5000],
                    "url": job_link,
                    "domain": detect_domain(full_text),
                    "technology": detect_technologies(full_text),
                    "experience_range": experience if experience else "Fresher",
                    "job_type": None,
                    "is_remote": False,
                    "is_walkin": is_walkin(full_text) or "walkin" in job_link.lower(),
                    "min_salary": min_salary,
                    "max_salary": max_salary,
                    "salary_currency": "INR",
                    "salary_period": "yearly" if min_salary else None,
                    "company_industry": None,
                    "company_logo": None,
                    "company_url": None,
                    "company_rating": None,
                    "company_reviews_count": None,
                    "company_num_employees": None,
                    "skills": None,
                    "vacancy_count": None,
                    "emails": None,
                    "date_posted": date_posted,
                    "source": "freshersworld",
                    "job_url_direct": None,
                })
            except Exception:
                continue

        return jobs

    def scrape(self, city: str) -> List[Dict]:
        """Scrape freshersworld.com category pages and filter jobs for the given city."""
        all_jobs = []
        city_lower = city.lower()

        for cat_path in self.CATEGORY_URLS:
            try:
                for page in range(self.MAX_PAGES):
                    if page == 0:
                        url = f"{self.BASE_URL}{cat_path}"
                    else:
                        url = f"{self.BASE_URL}{cat_path}?&limit={self.LIMIT}&offset={self.LIMIT * page}"

                    print(f"    [Freshersworld] Fetching page {page + 1}: {url}")
                    html = self._fetch_page(url)
                    if not html:
                        break

                    page_jobs = self._parse_jobs(html, city)
                    if not page_jobs:
                        print(f"    [Freshersworld] No jobs on page {page + 1}, stopping pagination.")
                        break

                    # Filter jobs that match the target city
                    city_jobs = [
                        j for j in page_jobs
                        if city_lower in (j.get("location_full") or "").lower()
                        or city_lower in (j.get("city") or "").lower()
                    ]
                    all_jobs.extend(city_jobs)
                    print(f"    [Freshersworld] Got {len(city_jobs)}/{len(page_jobs)} jobs matching {city} from page {page + 1}")

                    # Polite delay
                    time.sleep(random.uniform(1.0, 2.0))

            except Exception as e:
                print(f"    [Freshersworld] Error scraping {cat_path}: {e}")
                traceback.print_exc()

        # Deduplicate by URL
        seen = set()
        unique = []
        for j in all_jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique.append(j)

        print(f"  [Freshersworld] Total unique jobs for {city}: {len(unique)}")
        return unique
