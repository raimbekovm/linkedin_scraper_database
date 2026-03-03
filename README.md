# LinkedIn Scraper Database System

LinkedIn profile scraping system with database storage, web interface, and bulk search pipeline.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![SQLite](https://img.shields.io/badge/database-SQLite-green.svg)](https://www.sqlite.org/)
[![Flask](https://img.shields.io/badge/web-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-68%20passed-brightgreen.svg)]()

## Overview

System for scraping LinkedIn profiles by name from an Excel/CSV file, storing results in SQLite with full relationship mapping, and providing a web interface for search and analytics.

## Features

- **Bulk Search**: Read names from Excel/CSV, search LinkedIn, scrape profiles automatically
- **School Filter**: Filter LinkedIn search by university ID
- **Email Extraction**: Scrape email addresses from Contact Info overlay (when visible)
- **Profile Photos**: Download and store profile avatars
- **Relational Database**: SQLite with SQLAlchemy ORM, normalized schema (3NF)
- **Deduplication**: Automatic duplicate detection by LinkedIn URL
- **Rescrape Mode**: Option to update existing profiles instead of skipping them
- **Change Tracking**: Audit trail of all profile modifications
- **Timeout Protection**: Auto-skip profiles that hang for more than 120 seconds
- **Web Interface**: Flask dashboard with search, analytics, last scrape date, and export
- **Database Merge**: Combine multiple databases into one with deduplication
- **Export**: JSON, CSV, Excel formats
- **REST API**: Programmatic access to all data
- **Test Suite**: 68 pytest tests covering models, operations, export, and web routes

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/raimbekovm/linkedin_scraper_database.git
cd linkedin_scraper_database
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Launch Web Interface

```bash
python web/app.py
```

Open http://127.0.0.1:8080

### 3. Scrape Profiles by Name

```bash
# Search LinkedIn for names from a file
python scripts/search_and_scrape.py data/alumni_clean.xlsx

# With school filter (e.g. AUCA = 316375)
python scripts/search_and_scrape.py data/alumni_clean.xlsx --school-id 316375

# Process specific range
python scripts/search_and_scrape.py data/alumni_clean.xlsx --skip 100 --max-names 50 --school-id 316375

# Re-scrape existing profiles to update data
python scripts/search_and_scrape.py data/alumni_clean.xlsx --school-id 316375 --rescrape
```

### 4. Run Tests

```bash
pytest tests/ -v
```

## Architecture

```
linkedin_scraper/
├── database/                # Data layer
│   ├── models.py           # SQLAlchemy ORM (Person, Experience, Education, ProfileHistory)
│   ├── operations.py       # ProfileManager (CRUD, dedup, search) & AnalyticsManager
│   └── export.py           # DataExporter (JSON/CSV/Excel) & DataMigrator
├── web/                    # Presentation layer
│   ├── app.py             # Flask app (port 8080)
│   └── templates/         # Jinja2 templates
├── linkedin_scraper/       # Core scraping library
│   ├── person.py          # Profile scraper with email extraction
│   ├── person_search.py   # LinkedIn people search with school filter
│   ├── objects.py         # Data classes (Experience, Education, Contact)
│   ├── actions.py         # Authentication (email/password, cookie, manual login)
│   ├── company.py         # Company scraper
│   └── job_search.py      # Job search
├── scripts/               # Automation
│   ├── search_and_scrape.py   # Main pipeline: Excel/CSV -> search -> scrape -> DB
│   ├── scrape_to_database.py  # Direct URL scraping with photo download & timeout
│   ├── merge_databases.py     # Merge multiple databases into one
│   └── test_system.py         # System verification script
├── tests/                 # pytest test suite (68 tests)
└── data/                  # SQLite database & downloaded photos
```

## Search Pipeline

### Command Reference

```bash
python scripts/search_and_scrape.py <file> [options]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `file` | required | Path to CSV or Excel file with names |
| `--school-id` | none | LinkedIn school ID to filter search |
| `--skip` | 0 | Skip first N names |
| `--max-names` | 0 (all) | Max number of names to process |
| `--limit` | 1 | Search results to scrape per name |
| `--search-delay` | 5 | Seconds between searches |
| `--scrape-delay` | 3 | Seconds between scrapes |
| `--rescrape` | false | Re-scrape profiles already in the database |

### Authentication

The scraper tries authentication in this order:

1. **Environment variables** (auto-login):
   ```bash
   export LINKEDIN_EMAIL="your@email.com"
   export LINKEDIN_PASSWORD="yourpassword"
   ```
2. **Session cookie**:
   ```bash
   export LINKEDIN_COOKIE="your_li_at_cookie_value"
   ```
3. **Manual login**: Opens browser, waits for you to log in (120 sec timeout)

### What Gets Scraped

- Name, location, job title, company, about
- Email address (from Contact Info, if visible to your account)
- Employment history (position, company, dates, duration, description)
- Education history (institution, degree, dates)
- Profile photo (saved to `data/photos/`)

## Merging Databases

When scraping is split across multiple people, merge the results:

```bash
python scripts/merge_databases.py part1.db part2.db part3.db -o data/merged.db
```

Deduplicates by LinkedIn URL, keeps the most recent version, consolidates photos.

## Database Schema

| Table | Description | Key Fields |
|-------|-------------|------------|
| `persons` | Core profile data | linkedin_url (unique), name, location, job_title, company, about, email, photo_path |
| `experiences` | Employment history | person_id (FK), position_title, company_name, dates, duration |
| `educations` | Academic background | person_id (FK), institution_name, degree, dates |
| `profile_history` | Change audit trail | person_id (FK), changed_field, old_value, new_value, changed_at |

## Web Interface

| Route | Description |
|-------|-------------|
| `/` | Dashboard with stats, top companies/locations, last scrape date |
| `/profiles` | Paginated profile listing with last scrape date |
| `/profile/<id>` | Full profile detail with email, experiences, education, change history |
| `/search` | Multi-field search (name, company, location) |
| `/analytics` | Top 10 companies, locations, positions, education stats |
| `/export/<format>` | Download data as JSON, CSV, or Excel |

## REST API

- `GET /api/stats` — Database statistics
- `GET /api/profile/<id>` — Full profile JSON with experiences and educations
- `GET /export/json` — Download all profiles as JSON
- `GET /export/csv` — Download as CSV
- `GET /export/excel` — Download as Excel (multi-sheet)

## Credits

Based on [joeyism/linkedin_scraper](https://github.com/joeyism/linkedin_scraper), extended with database system, web interface, bulk search pipeline, email extraction, and merge tools.

## License

MIT License
