# LinkedIn Scraper Database System

LinkedIn profile scraping system with database storage, web interface, and bulk search pipeline.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![SQLite](https://img.shields.io/badge/database-SQLite-green.svg)](https://www.sqlite.org/)
[![Flask](https://img.shields.io/badge/web-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-66%20passed-brightgreen.svg)]()

## Overview

System for scraping LinkedIn profiles by name from an Excel/CSV file, storing results in SQLite with full relationship mapping, and providing a web interface for search and analytics.

## Features

- **Bulk Search**: Read names from Excel/CSV, search LinkedIn, scrape profiles automatically
- **School Filter**: Filter LinkedIn search by university ID
- **Profile Photos**: Download and store profile avatars
- **Relational Database**: SQLite with SQLAlchemy ORM, normalized schema (3NF)
- **Deduplication**: Automatic duplicate detection by LinkedIn URL
- **Change Tracking**: Audit trail of all profile modifications
- **Web Interface**: Flask dashboard with search, analytics, and export
- **Database Merge**: Combine multiple databases into one with deduplication
- **Export**: JSON, CSV, Excel formats
- **REST API**: Programmatic access to all data
- **Test Suite**: 66 pytest tests covering models, operations, export, and web routes

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

Open http://127.0.0.1:8080 — the database already contains sample profiles.

### 3. Scrape Profiles by Name

```bash
# Search LinkedIn for names from a file
python scripts/search_and_scrape.py data/alumni.csv

# With school filter
python scripts/search_and_scrape.py data/alumni.xlsx --school-id 316375

# Process specific range
python scripts/search_and_scrape.py data/alumni.xlsx --skip 100 --max-names 50 --school-id 316375
```

### 4. Run Tests

```bash
pytest tests/ -v
```

## Architecture

```
linkedin_scraper/
├── database/                # Data layer
│   ├── models.py           # SQLAlchemy ORM models (Person, Experience, Education, ProfileHistory)
│   ├── operations.py       # ProfileManager (CRUD, dedup, search) & AnalyticsManager
│   └── export.py           # DataExporter (JSON/CSV/Excel) & DataMigrator
├── web/                    # Presentation layer
│   ├── app.py             # Flask app (port 8080) with input validation
│   └── templates/         # Jinja2 templates (dashboard, profiles, search, analytics)
├── linkedin_scraper/       # Core scraping library
│   ├── person.py          # Person profile scraper (Selenium)
│   ├── person_search.py   # LinkedIn people search with school filter
│   ├── objects.py         # Data classes (Experience, Education, Contact, Scraper base)
│   ├── actions.py         # Authentication (email/password, cookie, manual login)
│   ├── company.py         # Company scraper
│   └── job_search.py      # Job search
├── scripts/               # Automation
│   ├── search_and_scrape.py   # Main pipeline: Excel/CSV -> search -> scrape -> DB
│   ├── scrape_to_database.py  # Direct URL scraping with photo download
│   ├── merge_databases.py     # Merge multiple databases into one
│   └── test_system.py         # System verification script
├── tests/                 # pytest test suite (66 tests)
│   ├── conftest.py        # Fixtures with in-memory SQLite
│   ├── test_models.py     # ORM model tests
│   ├── test_operations.py # ProfileManager & AnalyticsManager tests
│   ├── test_export.py     # Export functionality tests
│   └── test_web.py        # Flask route & input validation tests
├── data/                  # Data storage
│   ├── linkedin_profiles.db   # SQLite database
│   └── photos/                # Downloaded profile photos
└── docs/                  # Technical documentation
```

## Search Pipeline

The main pipeline reads names from an Excel/CSV file, searches LinkedIn for each person, and scrapes found profiles into the database.

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

### Input File Format

CSV or Excel with a column named `name` (case-insensitive), or uses the first column:

```csv
name
John Doe
Jane Smith
```

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

For each found profile:
- Name, location, job title, company, about
- Full employment history (position, company, dates, duration, description)
- Education history (institution, degree, dates)
- Profile photo (saved to `data/photos/`)

## Merging Databases

When scraping is done in parts (or by multiple people), merge the results:

```bash
python scripts/merge_databases.py part1.db part2.db part3.db -o data/merged.db
```

The merge script deduplicates by LinkedIn URL, keeps the most recent version of each profile, and consolidates photos.

## Database Schema

### Tables

| Table | Description | Key Fields |
|-------|-------------|------------|
| `persons` | Core profile data | linkedin_url (unique), name, location, job_title, company, about, photo_path |
| `experiences` | Employment history | person_id (FK), position_title, company_name, dates, duration |
| `educations` | Academic background | person_id (FK), institution_name, degree, dates |
| `profile_history` | Change audit trail | person_id (FK), changed_field, old_value, new_value, changed_at |

### Relationships

- Person -> Experiences (1:N, cascade delete)
- Person -> Educations (1:N, cascade delete)
- Person -> ProfileHistory (1:N, cascade delete)

## Web Interface

| Route | Description |
|-------|-------------|
| `/` | Dashboard with stats, top companies/locations, export buttons |
| `/profiles` | Paginated profile listing (20 per page) |
| `/profile/<id>` | Full profile detail with experiences, education, change history |
| `/search` | Multi-field search (name, company, location) |
| `/analytics` | Top 10 companies, locations, positions, education stats |

## REST API

### GET /api/stats
```json
{
  "total_persons": 17,
  "total_experiences": 76,
  "total_educations": 36,
  "active_persons": 17
}
```

### GET /api/profile/\<id\>
```json
{
  "id": 1,
  "name": "John Doe",
  "linkedin_url": "https://www.linkedin.com/in/johndoe/",
  "current_job_title": "Software Engineer",
  "experiences": [...],
  "educations": [...]
}
```

### Export

- `GET /export/json` — Download all profiles as JSON
- `GET /export/csv` — Download as CSV
- `GET /export/excel` — Download as Excel (multi-sheet)

## Python API

```python
from database.operations import ProfileManager, AnalyticsManager
from database.export import DataExporter

pm = ProfileManager()
am = AnalyticsManager()

# Search profiles
results = pm.search_profiles(query="John", company="Google", location="San Francisco")

# Analytics
top_companies = am.get_top_companies(limit=10)

# Export
exporter = DataExporter()
exporter.export_to_json('profiles.json')
exporter.export_to_excel('profiles.xlsx')
```

## Development

### Requirements

- Python 3.9+
- Google Chrome (for Selenium scraping)
- LinkedIn account (for authentication)

### Running Tests

```bash
pytest tests/ -v
```

Tests use in-memory SQLite and don't require Chrome or LinkedIn.

## Credits

Based on [joeyism/linkedin_scraper](https://github.com/joeyism/linkedin_scraper), extended with database system, web interface, bulk search pipeline, and merge tools.

## License

MIT License
