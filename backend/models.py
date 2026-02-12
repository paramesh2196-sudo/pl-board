from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Date
from sqlalchemy.sql import func
from database import Base


class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(Integer, primary_key=True, index=True)

    # Core fields
    title = Column(String, index=True)
    company = Column(String, index=True)
    city = Column(String, index=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True, default="India")
    location_full = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String, unique=True, index=True)

    # Classification
    domain = Column(String, nullable=True, index=True)
    technology = Column(String, nullable=True, index=True)
    experience_range = Column(String, nullable=True)
    job_type = Column(String, nullable=True)  # fulltime, parttime, internship, contract
    is_remote = Column(Boolean, default=False)
    is_walkin = Column(Boolean, default=False)

    # Compensation
    min_salary = Column(Float, nullable=True)
    max_salary = Column(Float, nullable=True)
    salary_currency = Column(String, nullable=True)
    salary_period = Column(String, nullable=True)  # yearly, monthly, etc.

    # Company details
    company_industry = Column(String, nullable=True)
    company_logo = Column(String, nullable=True)
    company_url = Column(String, nullable=True)
    company_rating = Column(Float, nullable=True)
    company_reviews_count = Column(Integer, nullable=True)
    company_num_employees = Column(String, nullable=True)

    # Job meta
    skills = Column(Text, nullable=True)  # comma-separated
    vacancy_count = Column(Integer, nullable=True)
    emails = Column(Text, nullable=True)  # comma-separated emails found in description

    # Dates & Source
    date_posted = Column(Date, nullable=True)
    posted_date = Column(DateTime(timezone=True), server_default=func.now())  # when we scraped it
    source = Column(String, index=True)  # indeed, linkedin, naukri, etc.
    job_url_direct = Column(String, nullable=True)  # direct apply link
