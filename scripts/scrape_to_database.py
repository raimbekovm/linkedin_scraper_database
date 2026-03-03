"""
LinkedIn profile scraper with database integration.

Scrapes LinkedIn profiles using Selenium and stores data in SQLite database
with support for deduplication and change tracking.
"""

import time
import sys
import os
import logging
import re
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_scraper import Person
from linkedin_scraper.actions import login
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from database.operations import ProfileManager
from database.models import get_db_manager

logger = logging.getLogger(__name__)

LOGIN_CHECK_INTERVAL = 5
LOGIN_TIMEOUT = 120


def create_driver():
    """Create and return a configured Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def authenticate(driver):
    """
    Authenticate with LinkedIn using env vars or manual login.

    Tries in order:
      1. LINKEDIN_EMAIL + LINKEDIN_PASSWORD (auto-login)
      2. LINKEDIN_COOKIE (session cookie)
      3. Manual login with smart wait (detects login automatically)
    """
    print("\n" + "=" * 60)
    print("LINKEDIN AUTHENTICATION")
    print("=" * 60)

    email = os.environ.get('LINKEDIN_EMAIL')
    password = os.environ.get('LINKEDIN_PASSWORD')
    cookie = os.environ.get('LINKEDIN_COOKIE')

    if email and password:
        print("Auto-login with LINKEDIN_EMAIL / LINKEDIN_PASSWORD...")
        login(driver, email=email, password=password)
        print("Login successful.")
    elif cookie:
        print("Auto-login with LINKEDIN_COOKIE...")
        login(driver, cookie=cookie)
        print("Cookie set. Verifying session...")
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
    else:
        print("No credentials found in environment variables.")
        print("Set LINKEDIN_EMAIL + LINKEDIN_PASSWORD or LINKEDIN_COOKIE for auto-login.")
        print()
        print("Falling back to manual login...")
        driver.get("https://www.linkedin.com/login")
        print(f"Log in in the browser. Timeout: {LOGIN_TIMEOUT} seconds.")

        elapsed = 0
        while elapsed < LOGIN_TIMEOUT:
            time.sleep(LOGIN_CHECK_INTERVAL)
            elapsed += LOGIN_CHECK_INTERVAL
            try:
                from linkedin_scraper.objects import Scraper
                checker = Scraper.__new__(Scraper)
                checker.driver = driver
                checker.WAIT_FOR_ELEMENT_TIMEOUT = 2
                if checker.is_signed_in():
                    print("Login detected!")
                    break
            except Exception:
                pass
            remaining = LOGIN_TIMEOUT - elapsed
            if remaining > 0:
                print(f"Waiting for login... {remaining}s remaining")
        else:
            print("WARNING: Login timeout reached. Proceeding anyway...")


PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'photos')


def get_profile_photo_url(driver):
    """Extract profile photo URL from the current LinkedIn profile page."""
    try:
        img = driver.find_element(
            By.CSS_SELECTOR,
            'img.pv-top-card-profile-picture__image--show'
        )
        src = img.get_attribute('src')
        if src and 'ghost' not in src and 'data:image' not in src:
            return src
    except Exception:
        pass
    try:
        img = driver.find_element(
            By.CSS_SELECTOR,
            '.pv-top-card-profile-picture img'
        )
        src = img.get_attribute('src')
        if src and 'ghost' not in src and 'data:image' not in src:
            return src
    except Exception:
        pass
    return None


def download_photo(photo_url: str, linkedin_url: str) -> str:
    """Download profile photo and return the saved file path relative to project."""
    os.makedirs(PHOTOS_DIR, exist_ok=True)

    # Extract username from LinkedIn URL for filename
    match = re.search(r'/in/([^/?]+)', linkedin_url)
    username = match.group(1) if match else 'unknown'
    filename = f"{username}.jpg"
    filepath = os.path.join(PHOTOS_DIR, filename)

    try:
        resp = requests.get(photo_url, timeout=15)
        resp.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(resp.content)
        return f"data/photos/{filename}"
    except Exception as e:
        logger.warning(f"Failed to download photo: {e}")
        return None


def scrape_profile_to_db(profile_url: str, driver, pm: ProfileManager, track_changes: bool = True):
    """
    Scrape LinkedIn profile and save to database.

    Args:
        profile_url: LinkedIn profile URL
        driver: Selenium WebDriver instance
        pm: ProfileManager instance
        track_changes: Whether to track changes in profile history

    Returns:
        Person object if successful, None otherwise
    """
    try:
        print(f"\nScraping: {profile_url}")

        # Scrape profile (skip contacts to avoid redirect to connections page)
        person = Person(profile_url, driver=driver, scrape=False)
        person.scrape_contacts = False
        person.scrape(close_on_complete=False)

        # Prepare data for saving
        experiences = []
        if hasattr(person, 'experiences') and person.experiences:
            for exp in person.experiences:
                experiences.append({
                    'position_title': exp.position_title,
                    'institution_name': exp.institution_name,
                    'location': exp.location,
                    'from_date': exp.from_date,
                    'to_date': exp.to_date,
                    'duration': exp.duration,
                    'description': exp.description
                })

        educations = []
        if hasattr(person, 'educations') and person.educations:
            for edu in person.educations:
                educations.append({
                    'institution_name': edu.institution_name,
                    'degree': edu.degree,
                    'from_date': edu.from_date,
                    'to_date': edu.to_date,
                    'description': edu.description
                })

        # Download profile photo
        photo_path = None
        photo_url = get_profile_photo_url(driver)
        if photo_url:
            photo_path = download_photo(photo_url, profile_url)

        profile_data = {
            'linkedin_url': profile_url,
            'name': person.name,
            'location': getattr(person, 'location', None),
            'job_title': getattr(person, 'job_title', None),
            'company': getattr(person, 'company', None),
            'about': getattr(person, 'about', None),
            'email': getattr(person, 'email', None),
            'photo_path': photo_path,
            'experiences': experiences,
            'educations': educations
        }

        # Save to database
        saved_person = pm.save_profile(profile_data, track_changes=track_changes)

        print(f"SUCCESS: Profile saved to database (ID: {saved_person.id})")
        print(f"  - Name: {saved_person.name}")
        print(f"  - Company: {saved_person.current_company}")
        print(f"  - Experience: {len(experiences)} positions")
        print(f"  - Education: {len(educations)} institutions")
        print(f"  - Email: {getattr(person, 'email', None) or 'not available'}")
        print(f"  - Photo: {photo_path or 'not available'}")
        print(f"  - Scrape count: {saved_person.scrape_count}")

        return saved_person

    except Exception as e:
        print(f"ERROR: Scraping failed for {profile_url}: {e}")
        logger.exception("Scraping error")
        return None


def main():
    """Main function for scraping LinkedIn profiles."""

    # Initialize database
    print("="*60)
    print("SYSTEM INITIALIZATION")
    print("="*60)

    db = get_db_manager()
    db.create_all_tables()
    pm = ProfileManager()

    stats = db.get_stats()
    print(f"\nCurrent database statistics:")
    print(f"  - Profiles: {stats['total_persons']}")
    print(f"  - Experience records: {stats['total_experiences']}")
    print(f"  - Education records: {stats['total_educations']}")
    print(f"  - History records: {stats['total_history_records']}")

    driver = create_driver()

    try:
        authenticate(driver)

        # List of profiles to scrape — add LinkedIn profile URLs here
        profiles_to_scrape = [
            # "https://www.linkedin.com/in/username1/",
            # "https://www.linkedin.com/in/username2/",
        ]

        if not profiles_to_scrape:
            print("No profiles to scrape. Add URLs to profiles_to_scrape list.")
            print("Or use search_and_scrape.py for bulk search by name.")
            driver.quit()
            return

        print("\n" + "="*60)
        print(f"STARTING SCRAPING ({len(profiles_to_scrape)} profiles)")
        print("="*60)

        successful = 0
        failed = 0

        for idx, profile_url in enumerate(profiles_to_scrape, 1):
            print(f"\n[{idx}/{len(profiles_to_scrape)}] ", end="")

            result = scrape_profile_to_db(profile_url, driver, pm, track_changes=True)

            if result:
                successful += 1
            else:
                failed += 1

            # Brief pause between profiles
            if idx < len(profiles_to_scrape):
                print("\nPausing 5 seconds before next profile...")
                time.sleep(5)

        # Final statistics
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"SUCCESS: Successful: {successful}")
        print(f"ERROR: Failed: {failed}")
        print(f"Total processed: {successful + failed}")

        # Updated database statistics
        stats = db.get_stats()
        print(f"\nUpdated database statistics:")
        print(f"  - Profiles: {stats['total_persons']}")
        print(f"  - Experience records: {stats['total_experiences']}")
        print(f"  - Education records: {stats['total_educations']}")
        print(f"  - History records: {stats['total_history_records']}")

        print("\n" + "="*60)
        print("Browser will close in 10 seconds...")
        time.sleep(10)

    except Exception as e:
        print(f"\nCritical error occurred: {e}")
        logger.exception("Critical error in main")
    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    main()
