"""
Internshala scraper using BeautifulSoup.
Based on the proven approach from KushalJain-00/Scraper repo.
Scrapes internshala.com for internships and fresher jobs across cities.
"""
import re
import time
import random
import traceback
import urllib3
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from scrapers.jobspy_scraper import detect_technologies, detect_domain, is_walkin, normalize_city

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IntershalaScraper(BaseScraper):
    """Scrapes internshala.com for internships/fresher jobs."""

    BASE_URL = "https://internshala.com/internships/"
    JOBS_URL = "https://internshala.com/jobs/"
    MAX_PAGES = 5

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
            "Referer": "https://internshala.com/",
        })

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic."""
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=15, verify=False)
                if resp.status_code != 200:
                    print(f"    [Internshala] Got status {resp.status_code} for {url}")
                    time.sleep(2)
                    continue
                return resp.text
            except requests.RequestException as e:
                print(f"    [Internshala] Attempt {attempt + 1} failed for {url}: {e}")
                time.sleep(2)
        return None

    def _extract_internship_data(self, card, target_city: str) -> Optional[Dict]:
        """Extract data from a single internship card using proven selectors."""
        try:
            # Title
            title_tag = card.find("h3")
            title = title_tag.text.strip() if title_tag else None
            if not title:
                return None

            # Company
            company_tag = card.find("p", class_="company-name")
            company = company_tag.text.strip() if company_tag else "Unknown"

            # Location — try multiple selectors
            location = ""
            location_tag = card.find("div", class_="row-1-item locations")
            if location_tag:
                location = location_tag.text.strip()
            else:
                location_tag = card.find("span", class_="location")
                if location_tag:
                    location = location_tag.text.strip()
            if not location:
                location = target_city

            # Stipend/Salary
            stipend_tag = card.find("span", class_="stipend")
            stipend = stipend_tag.text.strip() if stipend_tag else ""

            min_salary = None
            max_salary = None
            salary_period = None
            if stipend:
                # Parse salary like "₹10,000 /month" or "₹5,000 - ₹10,000 /month"
                nums = re.findall(r'[\d,]+', stipend.replace(",", ""))
                if len(nums) >= 2:
                    try:
                        min_salary = float(nums[0])
                        max_salary = float(nums[1])
                    except (ValueError, IndexError):
                        pass
                elif len(nums) == 1:
                    try:
                        min_salary = float(nums[0])
                    except ValueError:
                        pass
                if "month" in stipend.lower():
                    salary_period = "monthly"
                elif "year" in stipend.lower():
                    salary_period = "yearly"

            # Duration
            duration_tag = card.find("div", class_="row-1-item")
            duration = duration_tag.text.strip() if duration_tag else ""

            # Skills
            skill_tag = card.find("div", class_="job_skills")
            skills = skill_tag.text.strip().replace("\n", ", ") if skill_tag else ""

            # Link
            link_tag = card.find("a")
            link = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href:
                    link = f"https://internshala.com{href}" if not href.startswith("http") else href
            if not link:
                return None

            # Determine city
            city_name = normalize_city(location) or target_city

            full_text = f"{title} {company} {skills} {duration}"

            return {
                "title": title,
                "company": company,
                "city": city_name,
                "state": None,
                "country": "India",
                "location_full": location,
                "description": f"{title} at {company}. Skills: {skills}. Duration: {duration}".strip()[:5000],
                "url": link,
                "domain": detect_domain(full_text),
                "technology": detect_technologies(full_text) or skills,
                "experience_range": "Fresher",
                "job_type": "Internship",
                "is_remote": "remote" in location.lower() or "work from home" in location.lower(),
                "is_walkin": False,
                "min_salary": min_salary,
                "max_salary": max_salary,
                "salary_currency": "INR",
                "salary_period": salary_period,
                "company_industry": None,
                "company_logo": None,
                "company_url": None,
                "company_rating": None,
                "company_reviews_count": None,
                "company_num_employees": None,
                "skills": skills if skills else None,
                "vacancy_count": None,
                "emails": None,
                "date_posted": date.today(),
                "source": "internshala",
                "job_url_direct": link,
            }

        except Exception as e:
            return None

    def _scrape_search(self, search_query: str, city: str, base_url: str) -> List[Dict]:
        """Scrape Internshala for a given search query and city."""
        jobs = []
        city_slug = city.lower().replace(" ", "-")

        for page in range(1, self.MAX_PAGES + 1):
            try:
                if page == 1:
                    url = f"{base_url}{search_query}-internship"
                else:
                    url = f"{base_url}{search_query}-internship/page-{page}"

                # Add city filter
                url += f"/{city_slug}"

                print(f"    [Internshala] Fetching page {page}: {url}")
                html = self._fetch_page(url)
                if not html:
                    break

                soup = BeautifulSoup(html, "html.parser")

                # Primary selector from KushalJain-00 repo
                cards = soup.find_all("div", class_="internship_meta duration_meta")
                if not cards:
                    # Fallback selectors
                    cards = soup.find_all("div", class_="internship_meta")
                if not cards:
                    cards = soup.select(".individual_internship .internship_meta")

                if not cards:
                    print(f"    [Internshala] No cards on page {page}, stopping.")
                    break

                print(f"    [Internshala] Found {len(cards)} cards on page {page}")

                for card in cards:
                    try:
                        internship = self._extract_internship_data(card, city)
                        if internship:
                            jobs.append(internship)
                    except Exception:
                        continue

                time.sleep(random.uniform(1.5, 3.0))

            except Exception as e:
                print(f"    [Internshala] Error on page {page}: {e}")
                continue

        return jobs

    def scrape(self, city: str) -> List[Dict]:
        """Scrape Internshala for a given city."""
        all_jobs = []
        search_queries = ["fresher", "entry-level", "python", "java", "web-development"]

        for query in search_queries:
            try:
                jobs = self._scrape_search(query, city, self.BASE_URL)
                all_jobs.extend(jobs)
                print(f"    [Internshala] Got {len(jobs)} for '{query}' in {city}")
            except Exception as e:
                print(f"    [Internshala] Error with '{query}' in {city}: {e}")
                traceback.print_exc()

        # Deduplicate by URL
        seen = set()
        unique = []
        for j in all_jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique.append(j)

        print(f"  [Internshala] Total unique jobs for {city}: {len(unique)}")
        return unique
