"""
JobSpy-powered real scraper for PL Board.
Scrapes Indeed, LinkedIn, Glassdoor, Google Jobs, Naukri, and Internshala.
"""
import re
import traceback
from typing import List, Dict, Optional
from datetime import datetime, date
from scrapers.base_scraper import BaseScraper

# Technology keywords for auto-detection from description/title
TECH_KEYWORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue",
    "Node.js", "Django", "Flask", "Spring", "Spring Boot", ".NET", "C#", "C++",
    "Go", "Golang", "Rust", "Ruby", "PHP", "Laravel", "Swift", "Kotlin",
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "AWS", "Azure", "GCP",
    "Docker", "Kubernetes", "DevOps", "CI/CD", "Jenkins", "Git",
    "Machine Learning", "ML", "AI", "Data Science", "Deep Learning",
    "TensorFlow", "PyTorch", "NLP", "Computer Vision",
    "HTML", "CSS", "Tailwind", "Bootstrap", "SASS",
    "REST", "API", "GraphQL", "Microservices",
    "Android", "iOS", "Flutter", "React Native",
    "Selenium", "Testing", "QA", "Manual Testing", "Automation Testing",
    "SAP", "Salesforce", "Power BI", "Tableau",
    "Hadoop", "Spark", "Kafka", "ETL", "Data Engineering",
    "Cybersecurity", "Networking", "Linux", "Unix",
    "Figma", "UI/UX", "Photoshop",
    "Excel", "Word", "PowerPoint",
    "Tally", "Accounting",
]

# Domain keywords
DOMAIN_MAP = {
    "IT-Software": ["software", "developer", "engineer", "programming", "coding", "full stack", "backend", "frontend", "devops"],
    "Data Science": ["data scientist", "data analyst", "machine learning", "deep learning", "ai ", "artificial intelligence", "nlp", "data engineering"],
    "Web Development": ["web developer", "react", "angular", "vue", "frontend", "html", "css", "javascript developer"],
    "Mobile Development": ["android", "ios", "flutter", "react native", "mobile developer", "mobile app"],
    "Testing/QA": ["testing", "qa ", "quality assurance", "selenium", "automation testing", "manual testing", "test engineer"],
    "Database/DBA": ["database", "dba", "sql", "mysql", "postgresql", "mongodb", "oracle db"],
    "Cloud/DevOps": ["cloud", "aws", "azure", "gcp", "devops", "docker", "kubernetes", "ci/cd"],
    "Networking": ["network", "cisco", "ccna", "ccnp", "firewall", "cybersecurity", "security"],
    "Design/UI-UX": ["designer", "ui/ux", "ux ", "ui ", "figma", "photoshop", "graphic design"],
    "Sales/Marketing": ["sales", "marketing", "digital marketing", "seo", "sem", "social media"],
    "Finance/Accounting": ["finance", "accounting", "tally", "chartered accountant", "ca ", "accounts"],
    "HR/Recruitment": ["hr ", "human resource", "recruitment", "talent acquisition", "payroll"],
    "Content/Writing": ["content writer", "copywriter", "technical writer", "editor", "blog"],
    "Support/BPO": ["customer support", "bpo", "call center", "helpdesk", "voice process", "non-voice"],
    "Management": ["project manager", "product manager", "scrum master", "agile", "program manager"],
    "Mechanical/Civil": ["mechanical", "civil", "structural", "autocad", "solidworks"],
    "Electrical/Electronics": ["electrical", "electronics", "embedded", "vlsi", "pcb"],
}

# Walk-in keywords
WALKIN_KEYWORDS = [
    "walk-in", "walkin", "walk in", "direct interview", "spot offer",
    "spot interview", "open interview", "direct walk", "mega drive",
    "hiring drive", "recruitment drive", "job fair",
]

# City name normalization
CITY_ALIASES = {
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
    "hyderabad": "Hyderabad",
    "chennai": "Chennai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "pune": "Pune",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "noida": "Noida",
    "delhi": "Delhi",
    "new delhi": "Delhi",
}


def detect_technologies(text: str) -> str:
    """Detect technologies mentioned in job title/description."""
    if not text:
        return ""
    found = []
    text_lower = text.lower()
    for tech in TECH_KEYWORDS:
        # Use word boundary matching for short keywords
        if len(tech) <= 3:
            if re.search(rf'\b{re.escape(tech)}\b', text, re.IGNORECASE):
                found.append(tech)
        else:
            if tech.lower() in text_lower:
                found.append(tech)
    return ", ".join(found[:10]) if found else ""


def detect_domain(text: str) -> str:
    """Detect job domain from title/description."""
    if not text:
        return "General"
    text_lower = text.lower()
    for domain, keywords in DOMAIN_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return domain
    return "General"


def is_walkin(text: str) -> bool:
    """Check if the job is a walk-in interview."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in WALKIN_KEYWORDS)


def normalize_city(location_str: str) -> str:
    """Normalize city name from location string."""
    if not location_str:
        return ""
    loc_lower = location_str.lower().strip()
    for alias, canonical in CITY_ALIASES.items():
        if alias in loc_lower:
            return canonical
    return ""


class JobSpyScraper(BaseScraper):
    """
    Real scraper using the python-jobspy library.
    Scrapes: Indeed, LinkedIn, Glassdoor, Google Jobs, Naukri, Internshala
    """

    def __init__(self):
        # Sites to scrape - India-focused
        self.india_sites = ["indeed", "linkedin", "google", "naukri", "glassdoor"]
        self.results_per_city = 25  # per site batch
        self.hours_old = 72  # last 72 hours for better coverage

    def scrape(self, city: str) -> List[Dict]:
        """Scrape all supported sites for a given city."""
        from jobspy import scrape_jobs

        all_jobs = []
        search_queries = [
            f"walkin fresher {city}",
            f"walk-in interview fresher",
            f"fresher jobs",
        ]

        for query in search_queries:
            # First try all sites together
            try:
                print(f"  [JobSpy] Scraping '{query}' in {city} (all sites)...")
                jobs_df = scrape_jobs(
                    site_name=self.india_sites,
                    search_term=query,
                    location=city,
                    results_wanted=self.results_per_city,
                    hours_old=self.hours_old,
                    country_indeed="India",
                    linkedin_fetch_description=False,  # faster
                )

                if jobs_df is not None and len(jobs_df) > 0:
                    print(f"    Found {len(jobs_df)} jobs for '{query}' in {city}")
                    for _, row in jobs_df.iterrows():
                        try:
                            job = self._process_row(row, city)
                            if job:
                                all_jobs.append(job)
                        except Exception as e:
                            print(f"    Error processing job row: {e}")
                            continue
                else:
                    print(f"    No jobs found for '{query}' in {city} (batch), trying individually...")
                    raise Exception("Batch returned no results, trying individual sites")

            except Exception as e:
                print(f"    Batch scrape issue for '{query}' in {city}: {e}")
                # Fallback: try each site individually
                for site in self.india_sites:
                    try:
                        print(f"    [JobSpy] Trying {site} individually for '{query}' in {city}...")
                        jobs_df = scrape_jobs(
                            site_name=[site],
                            search_term=query,
                            location=city,
                            results_wanted=self.results_per_city,
                            hours_old=self.hours_old,
                            country_indeed="India",
                            linkedin_fetch_description=False,
                        )
                        if jobs_df is not None and len(jobs_df) > 0:
                            print(f"      Found {len(jobs_df)} jobs from {site}")
                            for _, row in jobs_df.iterrows():
                                try:
                                    job = self._process_row(row, city)
                                    if job:
                                        all_jobs.append(job)
                                except Exception as e2:
                                    continue
                        else:
                            print(f"      No jobs from {site}")
                    except Exception as site_err:
                        print(f"      {site} failed: {site_err}")
                        continue

        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)

        print(f"  [JobSpy] Total unique jobs for {city}: {len(unique_jobs)}")
        return unique_jobs

    def _process_row(self, row, target_city: str) -> Optional[Dict]:
        """Convert a pandas row from jobspy into our dict format."""
        title = str(row.get("title", "")) if row.get("title") else ""
        company = str(row.get("company", "")) if row.get("company") else "Unknown"
        description = str(row.get("description", "")) if row.get("description") else ""
        location = str(row.get("location", "")) if row.get("location") else ""
        job_url = str(row.get("job_url", "")) if row.get("job_url") else ""
        site = str(row.get("site", "")) if row.get("site") else ""

        if not job_url or not title:
            return None

        # Combine text for analysis
        full_text = f"{title} {description}"

        # Determine city
        city = normalize_city(location)
        if not city:
            city = target_city  # Fallback to the city we searched for

        # Date posted
        date_posted_val = row.get("date_posted")
        if isinstance(date_posted_val, str):
            try:
                date_posted_val = datetime.strptime(date_posted_val, "%Y-%m-%d").date()
            except:
                date_posted_val = date.today()
        elif not isinstance(date_posted_val, date):
            date_posted_val = date.today()

        # Compensation
        min_salary = None
        max_salary = None
        salary_currency = None
        salary_period = None
        try:
            min_salary = float(row.get("min_amount")) if row.get("min_amount") else None
            max_salary = float(row.get("max_amount")) if row.get("max_amount") else None
            salary_currency = str(row.get("currency", "")) if row.get("currency") else "INR"
            salary_period = str(row.get("interval", "")) if row.get("interval") else None
        except:
            pass

        # Remote
        is_remote_val = False
        try:
            is_remote_val = bool(row.get("is_remote", False))
        except:
            pass

        # Job type
        job_type_val = str(row.get("job_type", "")) if row.get("job_type") else ""

        # Company details
        company_industry = str(row.get("company_industry", "")) if row.get("company_industry") else None
        company_logo = str(row.get("company_logo", "")) if row.get("company_logo") else None
        company_url = str(row.get("company_url", "")) if row.get("company_url") else None
        company_rating = None
        company_reviews_count = None
        company_num_employees = None
        try:
            company_rating = float(row.get("company_rating")) if row.get("company_rating") else None
            company_reviews_count = int(row.get("company_reviews_count")) if row.get("company_reviews_count") else None
            company_num_employees = str(row.get("company_num_employees", "")) if row.get("company_num_employees") else None
        except:
            pass

        # Skills & experience
        skills = str(row.get("skills", "")) if row.get("skills") else None
        experience_range = str(row.get("experience_range", "")) if row.get("experience_range") else None

        # Clean up NaN strings from pandas
        if skills and skills.lower() == "nan":
            skills = None
        if experience_range and experience_range.lower() == "nan":
            experience_range = None

        # Emails
        emails = str(row.get("emails", "")) if row.get("emails") else None
        if emails and emails.startswith("["):
            try:
                import ast
                emails = ", ".join(ast.literal_eval(emails))
            except:
                pass

        # Direct URL
        job_url_direct = str(row.get("job_url_direct", "")) if row.get("job_url_direct") else None

        # Vacancy
        vacancy_count = None
        try:
            vacancy_count = int(row.get("vacancy_count")) if row.get("vacancy_count") else None
        except:
            pass

        # Clean up any "nan" strings from pandas
        import math

        def clean_nan(val):
            if val is None:
                return None
            if isinstance(val, float) and math.isnan(val):
                return None
            if isinstance(val, str) and val.lower() == "nan":
                return None
            return val

        return {
            "title": clean_nan(title) or "Untitled",
            "company": clean_nan(company) or "Unknown",
            "city": city,
            "state": clean_nan(str(row.get("state", "")) if row.get("state") else None),
            "country": "India",
            "location_full": clean_nan(location) or "",
            "description": (clean_nan(description) or "")[:5000],
            "url": job_url,
            "domain": detect_domain(full_text),
            "technology": detect_technologies(full_text),
            "experience_range": clean_nan(experience_range),
            "job_type": clean_nan(job_type_val),
            "is_remote": is_remote_val,
            "is_walkin": is_walkin(full_text),
            "min_salary": clean_nan(min_salary),
            "max_salary": clean_nan(max_salary),
            "salary_currency": clean_nan(salary_currency),
            "salary_period": clean_nan(salary_period),
            "company_industry": clean_nan(company_industry),
            "company_logo": clean_nan(company_logo),
            "company_url": clean_nan(company_url),
            "company_rating": clean_nan(company_rating),
            "company_reviews_count": clean_nan(company_reviews_count),
            "company_num_employees": clean_nan(company_num_employees),
            "skills": clean_nan(skills),
            "vacancy_count": clean_nan(vacancy_count),
            "emails": clean_nan(emails),
            "date_posted": date_posted_val,
            "source": clean_nan(site) or "unknown",
            "job_url_direct": clean_nan(job_url_direct),
        }
