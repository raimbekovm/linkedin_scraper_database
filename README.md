# LinkedIn Scraper Database System

Enterprise-grade LinkedIn profile scraping system with relational database storage and web interface.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![SQLite](https://img.shields.io/badge/database-SQLite-green.svg)](https://www.sqlite.org/)
[![Flask](https://img.shields.io/badge/web-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

## Overview

This system extends the base LinkedIn scraper with a comprehensive database backend, web interface, and analytics capabilities. It demonstrates advanced database design, ORM usage, and full-stack development principles.

## Core Features

- **Relational Database**: SQLite with SQLAlchemy ORM, normalized schema (3NF)
- **Web Interface**: Flask-based dashboard with search and analytics
- **Data Deduplication**: Automatic duplicate detection and merging
- **Change Tracking**: Complete audit trail of profile modifications
- **Export Capabilities**: JSON, CSV, and Excel formats
- **REST API**: Programmatic access to all data

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/raimbekovm/linkedin_scraper_database.git
cd linkedin_scraper_database
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install sqlalchemy flask pandas openpyxl selenium requests lxml
```

### 4. Launch Web Interface

```bash
python web/app.py
```

**Access at:** `http://127.0.0.1:8080`

The database already contains sample profiles for demonstration.

### Optional: Run Scraper

To scrape additional profiles (requires LinkedIn login):

```bash
python scripts/scrape_to_database.py
```

## Architecture

```
linkedin_scraper/
├── database/           # Data layer
│   ├── models.py      # SQLAlchemy ORM models
│   ├── operations.py  # Business logic layer
│   └── export.py      # Data export utilities
├── web/               # Presentation layer
│   ├── app.py        # Flask application
│   └── templates/    # Jinja2 templates
├── scripts/          # Automation scripts
├── linkedin_scraper/ # Core scraping library
└── docs/             # Technical documentation
```

## Database Schema

### Tables

- **persons**: Core profile information with scraping metadata
- **experiences**: Employment history records
- **educations**: Academic background
- **profile_history**: Audit trail for all changes

### Relationships

- One-to-Many: Person → Experiences
- One-to-Many: Person → Educations
- One-to-Many: Person → ProfileHistory

### Indexes

Optimized for:
- Profile lookups by LinkedIn URL
- Search by name and location
- Company-based queries
- Change history retrieval

## Usage

### Profile Scraping

```python
from database.operations import ProfileManager
from linkedin_scraper import Person
from selenium import webdriver

pm = ProfileManager()
driver = webdriver.Chrome()

person = Person("https://linkedin.com/in/username", driver=driver)

profile_data = {
    'linkedin_url': "https://linkedin.com/in/username",
    'name': person.name,
    'location': person.location,
    'job_title': person.job_title,
    'company': person.company,
    'about': person.about,
    'experiences': [...],
    'educations': [...]
}

pm.save_profile(profile_data, track_changes=True)
```

### Data Retrieval

```python
from database.operations import ProfileManager, AnalyticsManager

pm = ProfileManager()
am = AnalyticsManager()

# Search profiles
results = pm.search_profiles(
    query="Software Engineer",
    company="Google",
    location="San Francisco"
)

# Get analytics
top_companies = am.get_top_companies(limit=10)
top_locations = am.get_top_locations(limit=10)
```

### Data Export

```python
from database.export import DataExporter

exporter = DataExporter()

exporter.export_to_json('profiles.json')
exporter.export_to_csv('profiles.csv')
exporter.export_to_excel('profiles.xlsx')
```

## Web Interface

### Dashboard (`/`)
- Database statistics overview
- Top companies, locations, and positions
- Quick export functionality

### Profiles (`/profiles`)
- Paginated profile listing
- Direct links to LinkedIn
- Access to detailed views

### Search (`/search`)
- Multi-field search (name, company, location)
- Real-time filtering
- Result pagination

### Analytics (`/analytics`)
- Top 10 rankings by category
- Educational institution statistics
- Export options for analysis

## REST API

### Endpoints

#### `GET /api/stats`
```json
{
  "total_persons": 150,
  "total_experiences": 450,
  "total_educations": 200,
  "active_persons": 148
}
```

#### `GET /api/profile/<id>`
```json
{
  "id": 1,
  "name": "John Doe",
  "linkedin_url": "https://...",
  "current_job_title": "Software Engineer",
  "experiences": [...],
  "educations": [...]
}
```

## Documentation

Comprehensive technical documentation available in `/docs/DATABASE_PROJECT_README.md`:

- ER diagrams
- Table specifications
- SQL query examples
- API reference
- Performance optimization guidelines

## Technical Highlights

### Database Design
- Third Normal Form (3NF) compliance
- Composite indexes for optimal query performance
- Foreign key constraints for referential integrity
- Soft delete pattern for data retention

### Code Quality
- Type hints throughout
- Comprehensive docstrings (Google style)
- Logging instead of print statements
- Proper exception handling

### Architecture Patterns
- Repository pattern for data access
- Factory pattern for object creation
- Singleton pattern for database connections
- MVC separation in web layer

## Original Library

This project extends [linkedin-scraper](https://github.com/joeyism/linkedin_scraper) with:
- Persistent data storage
- Web-based interface
- Analytics capabilities
- Deduplication system
- Change tracking

### Basic Scraper Usage

```python
from linkedin_scraper import Person, actions
from selenium import webdriver

driver = webdriver.Chrome()
actions.login(driver, email, password)

person = Person("https://www.linkedin.com/in/username", driver=driver)

print(person.name)
print(person.job_title)
print(person.company)
```

## Development

### Requirements
- Python 3.9+
- SQLAlchemy 2.0+
- Flask 3.0+
- Selenium 4.0+

### Testing
```bash
python scripts/test_system.py
```

## License

MIT License

## Credits

Original scraper: [joeyism/linkedin_scraper](https://github.com/joeyism/linkedin_scraper)

Database system and web interface: This repository
