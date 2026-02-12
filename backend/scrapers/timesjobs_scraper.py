"""
TimesJobs scraper using BeautifulSoup.
Note: TimesJobs has migrated to a Next.js SPA, so traditional scraping may
return limited results. SSL verification is disabled due to cert issues.
"""
import re
import traceback
import urllib3
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from scrapers.jobspy_scraper import detect_technologies, detect_domain, is_walkin, normalize_city

# Suppress SSL warnings since we use verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TimesJobsScraper(BaseScraper):
    """Scrapes TimesJobs.com for fresher/walk-in jobs."""

    BASE_URL = "https://www.timesjobs.com/candidate/job-search.html"

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    def scrape(self, city: str) -> List[Dict]:
        all_jobs = []
        queries = ["walk in fresher", "walkin fresher", "fresher", "entry level", "trainee"]

        for query in queries:
            try:
                jobs = self._scrape_query(query, city)
                all_jobs.extend(jobs)
                print(f"    [TimesJobs] Got {len(jobs)} jobs for '{query}' in {city}")
            except Exception as e:
                print(f"    [TimesJobs] Error scraping '{query}' in {city}: {e}")
                traceback.print_exc()

        # Deduplicate
        seen = set()
        unique = []
        for j in all_jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique.append(j)

        print(f"  [TimesJobs] Total unique jobs for {city}: {len(unique)}")
        return unique

    def _scrape_query(self, query: str, city: str) -> List[Dict]:
        jobs = []
        params = {
            "searchType": "personal498",
            "from": "submit",
            "txtKeywords": query,
            "txtLocation": city,
            "cboWorkExp1": "0",
            "cboWorkExp2": "2",
        }

        try:
            print(f"    [TimesJobs] Fetching '{query}' in {city}...")
            session = requests.Session()
            session.headers.update(self.headers)
            session.headers.update({
                "Referer": "https://www.timesjobs.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            resp = session.get(self.BASE_URL, params=params, timeout=20, verify=False)
            resp.raise_for_status()
            print(f"    [TimesJobs] Response status: {resp.status_code}, length: {len(resp.text)}")
        except Exception as e:
            print(f"    [TimesJobs] Request failed: {e}")
            traceback.print_exc()
            return jobs

        soup = BeautifulSoup(resp.text, "html.parser")
        job_cards = soup.find_all("li", class_="clearfix job-bx wht-shd-bx")
        if not job_cards:
            # Try alternate selectors
            job_cards = soup.find_all("li", class_="job-bx")
        if not job_cards:
            job_cards = soup.select(".srp-jobl .job-bx")

        print(f"    [TimesJobs] Found {len(job_cards)} cards for '{query}' in {city}")

        for card in job_cards:
            try:
                job = self._parse_card(card, city)
                if job:
                    jobs.append(job)
            except Exception as e:
                continue

        return jobs

    def _parse_card(self, card, target_city: str) -> Optional[Dict]:
        # Title & URL
        header = card.find("h2")
        if not header:
            return None
        link = header.find("a")
        if not link:
            return None

        title = link.text.strip()
        url = link.get("href", "").strip()
        if not url or not title:
            return None

        # Company
        company_tag = card.find("h3", class_="joblist-comp-name")
        company = company_tag.text.strip() if company_tag else "Unknown"

        # Description / Skills
        desc_tag = card.find("ul", class_="list-job-dtl")
        description = ""
        skills_text = ""
        if desc_tag:
            description = desc_tag.text.strip()
            # Try to get skills from the first <li> or specific span
            skill_spans = desc_tag.find_all("span", class_="srp-skills")
            if skill_spans:
                skills_text = ", ".join(s.text.strip() for s in skill_spans)

        # Location
        loc_tag = card.find("ul", class_="top-jd-dtl")
        location_text = ""
        experience_text = ""
        if loc_tag:
            spans = loc_tag.find_all("li")
            for span in spans:
                text = span.text.strip()
                header_el = span.find("i")
                if header_el:
                    icon_class = header_el.get("class", [])
                    if any("location" in c for c in icon_class):
                        # Remove the icon text, get location
                        location_text = span.text.replace(header_el.text, "").strip()
                    elif any("experience" in c or "exp" in c for c in icon_class):
                        experience_text = span.text.replace(header_el.text, "").strip()

        if not location_text:
            location_text = target_city

        # Posted date
        posted_tag = card.find("span", class_="sim-posted")
        date_posted = date.today()
        is_recent = True
        if posted_tag:
            posted_text = posted_tag.text.strip().lower()
            if "today" in posted_text or "just now" in posted_text or "few hours" in posted_text:
                date_posted = date.today()
            elif "yesterday" in posted_text or "1 day ago" in posted_text:
                date_posted = date.today() - timedelta(days=1)
            else:
                days_match = re.search(r'(\d+)\s*day', posted_text)
                if days_match:
                    days = int(days_match.group(1))
                    if days > 2:
                        is_recent = False
                    date_posted = date.today() - timedelta(days=days)
                else:
                    is_recent = False

        if not is_recent:
            return None  # Skip old postings

        # Build full text for analysis
        full_text = f"{title} {description} {skills_text}"
        city_name = normalize_city(location_text) or target_city

        return {
            "title": title,
            "company": company,
            "city": city_name,
            "state": None,
            "country": "India",
            "location_full": location_text,
            "description": description[:5000],
            "url": url,
            "domain": detect_domain(full_text),
            "technology": detect_technologies(full_text) or skills_text,
            "experience_range": experience_text if experience_text else "0-2 years",
            "job_type": None,
            "is_remote": False,
            "is_walkin": is_walkin(full_text),
            "min_salary": None,
            "max_salary": None,
            "salary_currency": "INR",
            "salary_period": None,
            "company_industry": None,
            "company_logo": None,
            "company_url": None,
            "company_rating": None,
            "company_reviews_count": None,
            "company_num_employees": None,
            "skills": skills_text if skills_text else None,
            "vacancy_count": None,
            "emails": None,
            "date_posted": date_posted,
            "source": "timesjobs",
            "job_url_direct": None,
        }
