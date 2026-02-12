from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, or_
from typing import List, Optional
from database import get_db, engine, Base
import models
from scrapers.scraper_manager import run_scrapers
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PL Board API - Real Job Scraper")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Scheduler Setup
scheduler = BackgroundScheduler()

# Tracking
last_scrape_time: Optional[str] = None
is_scraping: bool = False

def run_scrapers_task():
    """Helper to get a db session for the scheduler."""
    global last_scrape_time, is_scraping
    from database import SessionLocal
    is_scraping = True
    db = SessionLocal()
    try:
        run_scrapers(db)
        last_scrape_time = datetime.now().isoformat()
    finally:
        is_scraping = False
        db.close()

@app.on_event("startup")
def startup_event():
    # Schedule scraping every 24 hours
    scheduler.add_job(run_scrapers_task, 'interval', hours=24, id='daily_scrape')
    scheduler.start()

# ===================== Pydantic Schemas =====================

class JobOut(BaseModel):
    id: int
    title: str
    company: str
    city: str
    state: Optional[str] = None
    country: Optional[str] = None
    location_full: Optional[str] = None
    description: Optional[str] = None
    url: str
    domain: Optional[str] = None
    technology: Optional[str] = None
    experience_range: Optional[str] = None
    job_type: Optional[str] = None
    is_remote: bool = False
    is_walkin: bool = False
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    company_industry: Optional[str] = None
    company_logo: Optional[str] = None
    company_url: Optional[str] = None
    company_rating: Optional[float] = None
    company_reviews_count: Optional[int] = None
    company_num_employees: Optional[str] = None
    skills: Optional[str] = None
    vacancy_count: Optional[int] = None
    emails: Optional[str] = None
    date_posted: Optional[date] = None
    posted_date: Optional[datetime] = None
    source: str
    job_url_direct: Optional[str] = None

    class Config:
        from_attributes = True

class StatsOut(BaseModel):
    total_jobs: int
    jobs_today: int
    cities_count: int
    sources: dict
    domains: dict

# ===================== API Endpoints =====================

@app.post("/trigger-scrape")
def trigger_scrape():
    """Manually trigger the scraper in a background thread."""
    thread = threading.Thread(target=run_scrapers_task, daemon=True)
    thread.start()
    return {"message": "Scraping started in background. Check logs for progress."}

@app.get("/jobs")
def get_jobs(
    city: Optional[str] = None,
    technology: Optional[str] = None,
    domain: Optional[str] = None,
    source: Optional[str] = None,
    experience: Optional[str] = None,
    job_type: Optional[str] = None,
    is_walkin: Optional[bool] = None,
    is_remote: Optional[bool] = None,
    search: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    sort: str = "newest",
    days: int = 7,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get filtered job listings with pagination metadata."""
    query = db.query(models.JobListing)

    # Date window filter
    limit_date = datetime.now() - timedelta(days=days)
    query = query.filter(models.JobListing.posted_date >= limit_date)

    # City filter (handle common name variants)
    if city:
        city_variants = {city}
        variant_map = {
            "Bangalore": {"Bangalore", "Bengaluru", "bengaluru", "bangalore"},
            "Gurgaon": {"Gurgaon", "Gurugram", "gurgaon", "gurugram"},
            "Mumbai": {"Mumbai", "Bombay", "mumbai", "bombay"},
            "Chennai": {"Chennai", "Madras", "chennai", "madras"},
            "Kolkata": {"Kolkata", "Calcutta", "kolkata", "calcutta"},
            "Pune": {"Pune", "pune"},
            "Hyderabad": {"Hyderabad", "hyderabad"},
        }
        if city in variant_map:
            city_variants = variant_map[city]
        query = query.filter(
            or_(*[models.JobListing.city.ilike(v) for v in city_variants])
        )

    # Technology filter (partial match)
    if technology:
        query = query.filter(models.JobListing.technology.ilike(f"%{technology}%"))

    # Domain filter
    if domain:
        query = query.filter(models.JobListing.domain == domain)

    # Source filter
    if source:
        query = query.filter(models.JobListing.source == source)

    # Experience filter
    if experience:
        if experience == "fresher":
            query = query.filter(
                or_(
                    models.JobListing.experience_range.ilike("%fresher%"),
                    models.JobListing.experience_range == "0 Years",
                    models.JobListing.experience_range == "0 Yrs",
                    models.JobListing.experience_range.ilike("0 to %"),
                )
            )
        elif experience == "5+":
            # 5+ years: match anything with min >= 5
            query = query.filter(
                or_(
                    models.JobListing.experience_range.ilike("5-%"),
                    models.JobListing.experience_range.ilike("5 to %"),
                    models.JobListing.experience_range.ilike("6-%"),
                    models.JobListing.experience_range.ilike("6 to %"),
                    models.JobListing.experience_range.ilike("7-%"),
                    models.JobListing.experience_range.ilike("7 to %"),
                    models.JobListing.experience_range.ilike("8-%"),
                    models.JobListing.experience_range.ilike("8 to %"),
                    models.JobListing.experience_range.ilike("10-%"),
                    models.JobListing.experience_range.ilike("10 to %"),
                    models.JobListing.experience_range.ilike("15-%"),
                    models.JobListing.experience_range.ilike("16-%"),
                    models.JobListing.experience_range.ilike("%5+ Years%"),
                    models.JobListing.experience_range.ilike("5-8%"),
                    models.JobListing.experience_range.ilike("5-10%"),
                )
            )
        elif "-" in experience:
            # Range like "0-1", "1-3", "2-5", "3-5"
            parts = experience.split("-")
            low = int(parts[0])
            high = int(parts[1])
            conditions = []
            # Match exact values like "Fresher", "0 Years", etc.
            if low == 0:
                conditions.append(models.JobListing.experience_range.ilike("%fresher%"))
            for yr in range(low, high + 1):
                conditions.append(models.JobListing.experience_range == f"{yr} Years")
                conditions.append(models.JobListing.experience_range == f"{yr} Yrs")
                conditions.append(models.JobListing.experience_range == f"{yr}+ Years")
            # Match Naukri-style ranges "{lo}-{hi} Yrs" where both ends are within [low, high+2]
            for lo in range(low, high + 1):
                for hi in range(lo, high + 3):  # slight buffer above high
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo}-{hi} %"))
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo}-{hi}Yr%"))
            # Match Internshala/Freshersworld style "X to Y Years" where the range overlaps
            for lo in range(low, high + 1):
                for hi in range(lo, high + 3):
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo} to {hi} Year%"))
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo} to {hi}+%"))
            # Match fractional starts like "0.6 to 2 Years" — only where upper bound is in [low, high+1]
            for hi in range(max(low, 1), high + 2):
                conditions.append(models.JobListing.experience_range.ilike(f"%.% to {hi} Year%"))
                conditions.append(models.JobListing.experience_range.ilike(f"%.% to {hi}+%"))
            query = query.filter(or_(*conditions))
        else:
            # Single number like "1", "2", "3"
            yr = int(experience)
            conditions = [
                models.JobListing.experience_range == f"{yr} Years",
                models.JobListing.experience_range == f"{yr} Yrs",
                models.JobListing.experience_range == f"{yr}+ Years",
            ]
            # Match ranges where yr is within [low, high] e.g. "0-2 Yrs" contains 1
            # Match Naukri-style: "{low}-{high} Yrs"
            for lo in range(0, yr + 1):
                for hi in range(yr, yr + 4):  # reasonable upper bound
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo}-{hi} %"))
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo} to {hi} %"))
                    conditions.append(models.JobListing.experience_range.ilike(f"{lo} to {hi}+%"))
            # Also match "{yr}-X" patterns
            for hi in range(yr, yr + 4):
                conditions.append(models.JobListing.experience_range.ilike(f"{yr}-{hi}%"))
            # Match "X to yr" and "X to yr+" patterns
            for lo in range(0, yr + 1):
                conditions.append(models.JobListing.experience_range.ilike(f"{lo} to {yr} Year%"))
                conditions.append(models.JobListing.experience_range.ilike(f"{lo} to {yr}+%"))
                conditions.append(models.JobListing.experience_range.ilike(f"{lo}.% to {yr} Year%"))
                conditions.append(models.JobListing.experience_range.ilike(f"{lo}.% to {yr}+%"))
            query = query.filter(or_(*conditions))

    # Job type filter
    if job_type:
        query = query.filter(models.JobListing.job_type.ilike(f"%{job_type}%"))

    # Walk-in filter
    if is_walkin is not None:
        query = query.filter(models.JobListing.is_walkin == is_walkin)

    # Remote filter
    if is_remote is not None:
        query = query.filter(models.JobListing.is_remote == is_remote)

    # Salary filter
    if salary_min is not None:
        query = query.filter(models.JobListing.max_salary >= salary_min)
    if salary_max is not None:
        query = query.filter(models.JobListing.min_salary <= salary_max)

    # Full-text search across title, company, description, skills
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.JobListing.title.ilike(search_term),
                models.JobListing.company.ilike(search_term),
                models.JobListing.description.ilike(search_term),
                models.JobListing.skills.ilike(search_term),
            )
        )

    # Get total count before pagination
    total_count = query.count()

    # Sorting
    if sort == "salary_high":
        query = query.order_by(models.JobListing.max_salary.desc().nullslast(), models.JobListing.posted_date.desc())
    elif sort == "salary_low":
        query = query.order_by(models.JobListing.min_salary.asc().nullslast(), models.JobListing.posted_date.desc())
    elif sort == "company":
        query = query.order_by(models.JobListing.company.asc(), models.JobListing.posted_date.desc())
    else:  # newest
        query = query.order_by(models.JobListing.posted_date.desc())

    jobs = query.offset(offset).limit(limit).all()

    return {
        "jobs": [JobOut.model_validate(j) for j in jobs],
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count,
    }

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    total = db.query(sqlfunc.count(models.JobListing.id)).scalar()
    today_start = datetime.now() - timedelta(hours=24)
    today_count = db.query(sqlfunc.count(models.JobListing.id)).filter(
        models.JobListing.posted_date >= today_start
    ).scalar()
    cities_count = db.query(sqlfunc.count(sqlfunc.distinct(models.JobListing.city))).scalar()
    walkin_count = db.query(sqlfunc.count(models.JobListing.id)).filter(
        models.JobListing.is_walkin == True
    ).scalar()

    # Source breakdown
    source_rows = db.query(
        models.JobListing.source, sqlfunc.count(models.JobListing.id)
    ).group_by(models.JobListing.source).all()
    sources = {row[0]: row[1] for row in source_rows if row[0]}

    # Domain breakdown
    domain_rows = db.query(
        models.JobListing.domain, sqlfunc.count(models.JobListing.id)
    ).group_by(models.JobListing.domain).all()
    domains = {row[0]: row[1] for row in domain_rows if row[0]}

    # City breakdown
    city_rows = db.query(
        models.JobListing.city, sqlfunc.count(models.JobListing.id)
    ).group_by(models.JobListing.city).all()
    cities = {row[0]: row[1] for row in city_rows if row[0]}

    # Experience breakdown
    exp_rows = db.query(
        models.JobListing.experience_range, sqlfunc.count(models.JobListing.id)
    ).group_by(models.JobListing.experience_range).all()
    experiences = {(row[0] or "Not specified"): row[1] for row in exp_rows}

    return {
        "total_jobs": total or 0,
        "jobs_today": today_count or 0,
        "cities_count": cities_count or 0,
        "walkin_count": walkin_count or 0,
        "sources": sources,
        "domains": domains,
        "cities": cities,
        "experiences": experiences,
        "last_scrape_time": last_scrape_time,
        "is_scraping": is_scraping,
    }

@app.get("/filters/cities")
def get_cities(db: Session = Depends(get_db)):
    """Get distinct cities from database."""
    return [c[0] for c in db.query(models.JobListing.city).distinct().all() if c[0]]

@app.get("/filters/domains")
def get_domains(db: Session = Depends(get_db)):
    """Get distinct domains from database."""
    return [d[0] for d in db.query(models.JobListing.domain).distinct().all() if d[0]]

@app.get("/filters/sources")
def get_sources(db: Session = Depends(get_db)):
    """Get distinct sources from database."""
    return [s[0] for s in db.query(models.JobListing.source).distinct().all() if s[0]]

@app.get("/filters/technologies")
def get_technologies(db: Session = Depends(get_db)):
    """Get commonly found technologies."""
    return [
        "Python", "Java", "JavaScript", "React", "Angular", "Node.js",
        "SQL", "AWS", ".NET", "C++", "DevOps", "Docker", "Kubernetes",
        "Machine Learning", "Data Science", "Flutter", "Android", "iOS",
        "Testing", "Selenium", "SAP", "PHP", "Ruby", "Go",
    ]

@app.get("/filters/experiences")
def get_experiences(db: Session = Depends(get_db)):
    """Get distinct experience ranges from database."""
    rows = db.query(models.JobListing.experience_range).distinct().all()
    values = sorted(set(r[0] for r in rows if r[0] and r[0].lower() != "nan"))
    return values

@app.get("/filters/job-types")
def get_job_types(db: Session = Depends(get_db)):
    """Get distinct job types from database."""
    rows = db.query(models.JobListing.job_type).distinct().all()
    values = sorted(set(r[0] for r in rows if r[0] and r[0].lower() != "nan"))
    return values

@app.get("/scrape-status")
def get_scrape_status():
    """Get current scraping status."""
    return {
        "is_scraping": is_scraping,
        "last_scrape_time": last_scrape_time,
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)
