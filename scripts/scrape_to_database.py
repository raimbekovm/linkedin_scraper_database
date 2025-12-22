"""
LinkedIn profile scraper with database integration.

Scrapes LinkedIn profiles using Selenium and stores data in SQLite database
with support for deduplication and change tracking.
"""

import time
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_scraper import Person
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from database.operations import ProfileManager
from database.models import get_db_manager

logger = logging.getLogger(__name__)


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

        # Scrape profile
        person = Person(profile_url, driver=driver, scrape=False)
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

        profile_data = {
            'linkedin_url': profile_url,
            'name': person.name,
            'location': getattr(person, 'location', None),
            'job_title': getattr(person, 'job_title', None),
            'company': getattr(person, 'company', None),
            'about': getattr(person, 'about', None),
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

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("\n" + "="*60)
        print("LINKEDIN AUTHENTICATION")
        print("="*60)
        print("1. Log in to LinkedIn in the opened browser")
        print("2. You have 60 seconds to complete login")
        print("3. Scraping will begin automatically")
        print("="*60 + "\n")

        # Open LinkedIn
        driver.get("https://www.linkedin.com/login")

        # Wait 60 seconds for manual login
        print("Waiting for login (60 seconds)...")
        for i in range(60, 0, -10):
            print(f"{i} seconds remaining...")
            time.sleep(10)

        # List of profiles to scrape (11 profiles for portfolio)
        profiles_to_scrape = [
            "https://www.linkedin.com/in/sultan-baisbekov-a079b4362/",
            "https://www.linkedin.com/in/nurbolot-piridinov/",
            "https://www.linkedin.com/in/amantai-akunov-52363b227/",
            "https://www.linkedin.com/in/baktygul-tazhamatova-389048208/",
            "https://www.linkedin.com/in/farzin-amonov-42812035a/",
            "https://www.linkedin.com/in/toichubek-pazylov/",
            "https://www.linkedin.com/in/aktan-toksumbaev-298131229/",
            "https://www.linkedin.com/in/aidarkazybekov/",
            "https://www.linkedin.com/in/bekzhan-eldiiar-uulu-4319a027a/",
            "https://www.linkedin.com/in/baitur-suiunbaev-142180303/",
            "https://www.linkedin.com/in/eldarsatyndiev/",
        ]

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
