# LinkedIn Scraper Database System - Technical Documentation

Detailed technical documentation for the LinkedIn profile scraping and database system.

## Contents

1. [System Architecture](#system-architecture)
2. [Database Schema](#database-schema)
3. [Scraping Pipeline](#scraping-pipeline)
4. [Merging Databases](#merging-databases)
5. [Web Interface & API](#web-interface--api)
6. [Data Export](#data-export)
7. [Testing](#testing)
8. [SQL Examples](#sql-examples)

---

## System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Excel/CSV   │  │  Direct URLs │  │  LinkedIn Search   │    │
│  │  alumni list │  │  (manual)    │  │  (by name/school)  │    │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘    │
└─────────┼─────────────────┼────────────────────┼────────────────┘
          │                 │                    │
          ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SCRAPING LAYER (Selenium)                   │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ search_and_      │  │ scrape_to_       │                    │
│  │ scrape.py        │  │ database.py      │                    │
│  │ (bulk pipeline)  │  │ (single/batch)   │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
│           │    ┌────────────────┐│                              │
│           ├───►│ PersonSearch   ││                              │
│           │    │ (person_search)││                              │
│           │    └────────────────┘│                              │
│           │    ┌────────────────┐│                              │
│           └───►│ Person         │◄                              │
│                │ (person.py)    │                               │
│                └────────┬───────┘                               │
│                         │ + photo download                     │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER (SQLAlchemy)                     │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ ProfileManager   │  │ AnalyticsManager │                    │
│  │ (CRUD, dedup,    │  │ (aggregations,   │                    │
│  │  change tracking)│  │  statistics)     │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
│           │                     │                              │
│           ▼                     ▼                              │
│  ┌──────────────────────────────────────────┐                  │
│  │              SQLite Database              │                  │
│  │  persons | experiences | educations |     │                  │
│  │  profile_history                         │                  │
│  └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
┌───────────────────┐     ┌──────────────────────────────┐
│   WEB LAYER       │     │      EXPORT LAYER            │
│   (Flask)         │     │  ┌─────┐ ┌─────┐ ┌───────┐  │
│                   │     │  │JSON │ │ CSV │ │ Excel │  │
│  Dashboard        │     │  └─────┘ └─────┘ └───────┘  │
│  Profiles         │     └──────────────────────────────┘
│  Search           │
│  Analytics        │     ┌──────────────────────────────┐
│  REST API         │     │      MERGE TOOL              │
└───────────────────┘     │  merge_databases.py          │
                          │  (combine team results)      │
                          └──────────────────────────────┘
```

### Module Dependencies

| Module | Depends On | Purpose |
|--------|-----------|---------|
| `database/models.py` | SQLAlchemy | ORM models, schema, DatabaseManager |
| `database/operations.py` | models.py | ProfileManager, AnalyticsManager |
| `database/export.py` | models.py, operations.py, pandas | DataExporter, DataMigrator |
| `linkedin_scraper/person.py` | objects.py, Selenium | Profile scraping |
| `linkedin_scraper/person_search.py` | objects.py, Selenium | LinkedIn people search |
| `linkedin_scraper/actions.py` | Selenium | Authentication |
| `scripts/scrape_to_database.py` | person.py, operations.py | Scraping + DB save + photo download |
| `scripts/search_and_scrape.py` | person_search.py, scrape_to_database.py | Bulk pipeline |
| `scripts/merge_databases.py` | models.py | Database merging |
| `web/app.py` | operations.py, export.py, Flask | Web interface |

---

## Database Schema

### ER Diagram

```
┌──────────────────────────┐
│         persons           │
├──────────────────────────┤
│ id          INTEGER PK    │──┐
│ linkedin_url VARCHAR(500) │  │  UNIQUE, NOT NULL
│ name        VARCHAR(200)  │  │  NOT NULL
│ location    VARCHAR(200)  │  │
│ current_job_title  (300)  │  │
│ current_company    (300)  │  │
│ about       TEXT          │  │
│ photo_path  VARCHAR(500)  │  │
│ first_scraped_at DATETIME │  │
│ last_scraped_at  DATETIME │  │
│ scrape_count INTEGER      │  │
│ is_active   BOOLEAN       │  │
└──────────────────────────┘  │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   experiences     │ │   educations     │ │   profile_history    │
├──────────────────┤ ├──────────────────┤ ├──────────────────────┤
│ id        PK      │ │ id        PK     │ │ id           PK      │
│ person_id FK ─────│ │ person_id FK ────│ │ person_id    FK ─────│
│ position_title    │ │ institution_name │ │ changed_field        │
│ company_name      │ │ degree           │ │ old_value            │
│ location          │ │ field_of_study   │ │ new_value            │
│ from_date         │ │ from_date        │ │ changed_at  DATETIME │
│ to_date           │ │ to_date          │ └──────────────────────┘
│ duration          │ │ description      │
│ description       │ └──────────────────┘
│ created_at        │
└──────────────────┘
```

### Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| PRIMARY | persons | id | Primary key |
| UNIQUE | persons | linkedin_url | Deduplication |
| idx_name_location | persons | name, location | Search optimization |
| idx_company | persons | current_company | Company queries |
| idx_person_company | experiences | person_id, company_name | Join optimization |
| idx_changed_at | profile_history | changed_at | History queries |

### Table Details

#### persons

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique ID |
| linkedin_url | VARCHAR(500) | UNIQUE, NOT NULL, indexed | LinkedIn profile URL |
| name | VARCHAR(200) | NOT NULL, indexed | Full name |
| location | VARCHAR(200) | | Current location |
| current_job_title | VARCHAR(300) | | Current position |
| current_company | VARCHAR(300) | indexed | Current employer |
| about | TEXT | | Bio/summary |
| photo_path | VARCHAR(500) | | Relative path to downloaded photo |
| first_scraped_at | DATETIME | NOT NULL | First scrape timestamp |
| last_scraped_at | DATETIME | NOT NULL | Last scrape timestamp |
| scrape_count | INTEGER | DEFAULT 1 | Times scraped |
| is_active | BOOLEAN | DEFAULT TRUE | Soft delete flag |

#### experiences

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Unique ID |
| person_id | INTEGER | FK -> persons.id, NOT NULL | Owner profile |
| position_title | VARCHAR(300) | NOT NULL | Job title |
| company_name | VARCHAR(300) | NOT NULL, indexed | Employer |
| location | VARCHAR(200) | | Work location |
| from_date | VARCHAR(50) | | Start date (text) |
| to_date | VARCHAR(50) | | End date (text) |
| duration | VARCHAR(100) | | Duration text |
| description | TEXT | | Role description |
| created_at | DATETIME | | Record creation time |

#### educations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Unique ID |
| person_id | INTEGER | FK -> persons.id, NOT NULL | Owner profile |
| institution_name | VARCHAR(300) | NOT NULL, indexed | School/university |
| degree | VARCHAR(300) | | Degree name |
| field_of_study | VARCHAR(300) | | Field/major |
| from_date | VARCHAR(50) | | Start date |
| to_date | VARCHAR(50) | | End date |
| description | TEXT | | Additional info |
| created_at | DATETIME | | Record creation time |

#### profile_history

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Unique ID |
| person_id | INTEGER | FK -> persons.id, NOT NULL | Owner profile |
| changed_field | VARCHAR(100) | NOT NULL | Which field changed |
| old_value | TEXT | | Previous value |
| new_value | TEXT | | New value |
| changed_at | DATETIME | NOT NULL, indexed | When the change occurred |

### Cascade Behavior

All child tables use `CASCADE DELETE` - deleting a person removes all related experiences, educations, and history records.

---

## Scraping Pipeline

### Single Profile Scraping

```bash
python scripts/scrape_to_database.py
```

Flow:
1. Initialize Chrome WebDriver (via `webdriver-manager`)
2. Authenticate with LinkedIn (3 methods)
3. For each profile URL:
   - Navigate to profile page
   - Extract: name, location, about, job title, company
   - Scroll and extract experiences (position, company, dates, duration, description)
   - Extract educations (institution, degree, dates)
   - Extract profile photo URL from `pv-top-card-profile-picture` element
   - Download photo to `data/photos/{username}.jpg`
   - Save to database via `ProfileManager.save_profile()`
4. Close browser

### Bulk Search Pipeline

```bash
python scripts/search_and_scrape.py data/alumni_clean.xlsx --school-id 316375
```

Flow:
1. Read names from Excel/CSV (auto-detect `name` column)
2. Apply `--skip` and `--max-names` filters
3. Initialize Chrome WebDriver and authenticate
4. For each name:
   - Build search URL: `https://www.linkedin.com/search/results/people/?keywords={name}&origin=FACETED_SEARCH&schoolFilter=["{school_id}"]`
   - Parse search results page for profile links (`a[href*="/in/"]`)
   - Extract profile URL, normalize it
   - Check if already in database (skip if exists)
   - Scrape profile and save (same as single pipeline)
   - Wait `--search-delay` seconds between searches
5. Print summary statistics

### Authentication Methods

| Priority | Method | Environment Variables | Notes |
|----------|--------|----------------------|-------|
| 1 | Email + Password | `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD` | Fully automated |
| 2 | Session Cookie | `LINKEDIN_COOKIE` | Use `li_at` cookie value |
| 3 | Manual Login | None | Browser opens, 120 sec timeout, auto-detects login |

### Rate Limiting

| Action | Default Delay | Flag |
|--------|--------------|------|
| Between searches | 5 seconds | `--search-delay` |
| Between scrapes | 3 seconds | `--scrape-delay` |
| Between profiles (direct) | 5 seconds | hardcoded |

---

## Merging Databases

When scraping is done in parts, merge the results into a single database:

```bash
python scripts/merge_databases.py part1.db part2.db part3.db -o data/merged.db
```

`scripts/merge_databases.py` handles:

- **Deduplication**: If same LinkedIn URL appears in multiple databases, keeps the one with the most recent `last_scraped_at`
- **Photo consolidation**: Copies photo files to a unified directory
- **Backup**: Creates `.backup` of existing output database before merging
- **Statistics**: Shows detailed counts of new, updated, and skipped profiles

---

## Web Interface & API

### Running the Web Server

```bash
python web/app.py
# Accessible at http://127.0.0.1:8080
```

### Pages

| Route | Description |
|-------|-------------|
| `GET /` | Dashboard: stats cards (profiles, active, experiences, educations), top 5 companies/locations/positions, export buttons |
| `GET /profiles` | Paginated profile list (20 per page), LinkedIn links, delete buttons |
| `GET /profile/<id>` | Full profile: experiences, educations, change history |
| `GET /search` | Search form: name (q), company, location. Max 100 results. Input sanitized to 200 chars |
| `GET /analytics` | Top 10 tables: companies, locations, positions, education institutions |

### REST API Endpoints

#### GET /api/stats

```json
{
  "total_persons": 17,
  "total_experiences": 76,
  "total_educations": 36,
  "total_history_records": 5,
  "active_persons": 17
}
```

#### GET /api/profile/\<id\>

```json
{
  "id": 9,
  "name": "Kanat Botbaev",
  "linkedin_url": "https://www.linkedin.com/in/kanat-botbaev-22a211142/",
  "location": "Kyrgyzstan",
  "current_job_title": "Director",
  "current_company": "Full-time",
  "about": "...",
  "scrape_count": 1,
  "experiences": [
    {
      "position_title": "Director",
      "company_name": "Some Company",
      "location": "Bishkek",
      "from_date": "Jan 2020",
      "to_date": "Present",
      "duration": "5 yrs",
      "description": "..."
    }
  ],
  "educations": [
    {
      "institution_name": "AUCA",
      "degree": "Bachelor of Arts",
      "from_date": "1993",
      "to_date": "1997"
    }
  ]
}
```

#### Export Endpoints

| Route | Format | Content-Type |
|-------|--------|-------------|
| `GET /export/json` | JSON file download | application/json |
| `GET /export/csv` | CSV file download | text/csv |
| `GET /export/excel` | Excel file download | application/vnd.openxmlformats |

### Security

- Input sanitization: search queries stripped and truncated to 200 chars
- Pagination clamping: page numbers bounded to valid range
- `maxlength="200"` on HTML input fields
- Flask `SECRET_KEY` from environment variable (falls back to random)

---

## Data Export

### DataExporter Class

```python
from database.export import DataExporter

exporter = DataExporter()

# JSON: Full nested structure with experiences and educations
count = exporter.export_to_json('profiles.json')

# CSV: Summary table (one row per profile, counts for experiences/educations)
count = exporter.export_to_csv('profiles.csv')

# Excel: Three sheets - Profiles, Experience, Education
count = exporter.export_to_excel('profiles.xlsx')
```

### Excel Sheet Structure

**Sheet 1: Profiles**
| ID | Name | Location | Position | Company | About | LinkedIn URL | First Scraped | Last Scraped | Scrape Count |

**Sheet 2: Experience**
| Profile ID | Name | Position | Company | Location | Start | End | Duration |

**Sheet 3: Education**
| Profile ID | Name | Institution | Degree | Start | End |

---

## Testing

### Test Suite Overview

66 tests across 4 modules, all using in-memory SQLite (no Chrome/LinkedIn needed):

| Module | Tests | Covers |
|--------|-------|--------|
| `test_models.py` | 11 | ORM models, table creation, relationships, cascade delete, repr |
| `test_operations.py` | 26 | ProfileManager CRUD, deduplication, change tracking, search, AnalyticsManager |
| `test_export.py` | 6 | JSON/CSV/Excel export, active_only filter, empty DB |
| `test_web.py` | 23 | All Flask routes, input validation, XSS protection, API endpoints |

### Running Tests

```bash
# All tests with verbose output
pytest tests/ -v

# Single module
pytest tests/test_models.py -v

# With coverage (if pytest-cov installed)
pytest tests/ --cov=database --cov=web -v
```

### Test Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_manager` | function, autouse | In-memory SQLite, patches get_db_manager in all modules |
| `pm` | function | ProfileManager instance |
| `am` | function | AnalyticsManager instance |
| `sample_profile_data` | function | Single profile dict with 2 experiences, 1 education |
| `populated_db` | function | 3 profiles (Alice/Google, Bob/Google, Carol/Meta) |
| `flask_client` | function | Flask test client with populated DB |

---

## SQL Examples

### Find all AUCA alumni

```sql
SELECT DISTINCT p.name, p.current_company, p.current_job_title
FROM persons p
JOIN educations e ON p.id = e.person_id
WHERE e.institution_name LIKE '%AUCA%'
   OR e.institution_name LIKE '%American University%Central Asia%'
ORDER BY p.name;
```

### Profiles with photos

```sql
SELECT name, linkedin_url, photo_path
FROM persons
WHERE photo_path IS NOT NULL AND is_active = 1
ORDER BY name;
```

### Top companies by alumni count

```sql
SELECT current_company, COUNT(*) as alumni_count
FROM persons
WHERE current_company IS NOT NULL AND is_active = 1
GROUP BY current_company
ORDER BY alumni_count DESC
LIMIT 20;
```

### People who worked at a specific company

```sql
SELECT DISTINCT p.name, p.location, ex.position_title, ex.from_date, ex.to_date
FROM persons p
JOIN experiences ex ON p.id = ex.person_id
WHERE ex.company_name LIKE '%Google%'
ORDER BY p.name;
```

### Profiles scraped in the last 7 days

```sql
SELECT name, linkedin_url, last_scraped_at, scrape_count
FROM persons
WHERE last_scraped_at >= datetime('now', '-7 days')
ORDER BY last_scraped_at DESC;
```

### Change history for a profile

```sql
SELECT ph.changed_field, ph.old_value, ph.new_value, ph.changed_at
FROM profile_history ph
JOIN persons p ON ph.person_id = p.id
WHERE p.name = 'Kanat Botbaev'
ORDER BY ph.changed_at DESC;
```

### Average experience count per person

```sql
SELECT
    AVG(exp_count) as avg_experiences,
    MIN(exp_count) as min_experiences,
    MAX(exp_count) as max_experiences
FROM (
    SELECT p.id, COUNT(ex.id) as exp_count
    FROM persons p
    LEFT JOIN experiences ex ON p.id = ex.person_id
    WHERE p.is_active = 1
    GROUP BY p.id
);
```

### Education statistics

```sql
SELECT
    e.institution_name,
    COUNT(DISTINCT e.person_id) as alumni_count,
    GROUP_CONCAT(DISTINCT e.degree) as degrees
FROM educations e
JOIN persons p ON e.person_id = p.id
WHERE p.is_active = 1
GROUP BY e.institution_name
ORDER BY alumni_count DESC
LIMIT 15;
```

---

## License

MIT License
