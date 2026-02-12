# PL Board - Job Dashboard

This is a dashboard to track daily walk-in interviews for freshers across major Indian cities.

## Project Structure

- `backend/`: Python FastAPI application with SQLite database and scrapers.
- `frontend/`: Next.js application with Tailwind CSS.

## Setup Instructions

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python main.py
   ```
   The API will be running at `http://localhost:8000`.

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   The dashboard will be available at `http://localhost:3000`.

## Scraping

The current implementation uses a **Mock Scraper** (`backend/scrapers/mock_scraper.py`) because scraping major job portals (LinkedIn, Naukri, Indeed) often requires handling CAPTCHAs, Proxies, and strict Terms of Service compliance, which cannot be universally solved in a simple script.

To implement real scraping:
1. Edit `backend/scrapers/mock_scraper.py` or create a new scraper file.
2. Use libraries like `playwright` or `selenium` to automate the browser.
3. Update `backend/scrapers/scraper_manager.py` to use your new scraper.
