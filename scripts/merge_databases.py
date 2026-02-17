"""
Merge multiple SQLite databases into one.

When a team splits the alumni list and each member scrapes their portion,
this script combines all individual databases into a single unified database.

Usage:
    python scripts/merge_databases.py db1.db db2.db db3.db
    python scripts/merge_databases.py db1.db db2.db -o merged.db
    python scripts/merge_databases.py *.db --photos-dir data/photos
"""

import sys
import os
import shutil
import argparse
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Person, Experience, Education, ProfileHistory, get_db_manager

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = 'data/linkedin_profiles_merged.db'
DEFAULT_PHOTOS_DIR = 'data/photos'


def open_source_db(db_path: str):
    """Open a source database and return a session."""
    engine = create_engine(f'sqlite:///{os.path.abspath(db_path)}')
    Session = sessionmaker(bind=engine)
    return Session()


def get_all_profiles(session) -> list:
    """Get all active profiles with relationships from a source database."""
    return session.query(Person).filter(Person.is_active == True).all()


def merge_databases(
    source_paths: list[str],
    output_path: str,
    photos_dir: str = DEFAULT_PHOTOS_DIR,
):
    """
    Merge multiple SQLite databases into one.

    Deduplicates by LinkedIn URL. If a profile exists in multiple sources,
    keeps the one with the most recent last_scraped_at date.

    Args:
        source_paths: List of paths to source .db files
        output_path: Path for the merged output database
        photos_dir: Directory to consolidate photos into
    """
    # Validate source files
    valid_sources = []
    for path in source_paths:
        if not os.path.exists(path):
            print(f"  WARNING: File not found, skipping: {path}")
            continue
        if os.path.abspath(path) == os.path.abspath(output_path):
            print(f"  WARNING: Skipping output file from sources: {path}")
            continue
        valid_sources.append(path)

    if not valid_sources:
        print("ERROR: No valid source databases found.")
        sys.exit(1)

    # Create output database
    if os.path.exists(output_path):
        backup = output_path + '.backup'
        shutil.copy2(output_path, backup)
        print(f"Backed up existing DB to: {backup}")

    output_db = get_db_manager(f'sqlite:///{os.path.abspath(output_path)}')
    output_db.create_all_tables()
    os.makedirs(photos_dir, exist_ok=True)

    # Counters
    total_profiles = 0
    new_profiles = 0
    updated_profiles = 0
    skipped_profiles = 0
    total_experiences = 0
    total_educations = 0
    photos_copied = 0

    print(f"\nMerging {len(valid_sources)} databases into: {output_path}")
    print("=" * 60)

    for src_idx, src_path in enumerate(valid_sources, 1):
        print(f"\n[{src_idx}/{len(valid_sources)}] Processing: {src_path}")

        try:
            src_session = open_source_db(src_path)
            profiles = get_all_profiles(src_session)
            print(f"  Found {len(profiles)} profiles")

            src_dir = os.path.dirname(os.path.abspath(src_path))

            for person in profiles:
                total_profiles += 1

                out_session = output_db.get_session()
                try:
                    # Check if profile already exists in output
                    existing = out_session.query(Person).filter(
                        Person.linkedin_url == person.linkedin_url
                    ).first()

                    if existing:
                        # Keep the more recent version
                        if person.last_scraped_at and existing.last_scraped_at:
                            if person.last_scraped_at > existing.last_scraped_at:
                                # Update with newer data
                                existing.name = person.name
                                existing.location = person.location
                                existing.current_job_title = person.current_job_title
                                existing.current_company = person.current_company
                                existing.about = person.about
                                existing.last_scraped_at = person.last_scraped_at
                                existing.scrape_count += person.scrape_count

                                # Update photo if new one exists
                                if person.photo_path and not existing.photo_path:
                                    existing.photo_path = person.photo_path

                                out_session.commit()
                                updated_profiles += 1
                            else:
                                skipped_profiles += 1
                        else:
                            skipped_profiles += 1
                    else:
                        # Create new profile
                        new_person = Person(
                            linkedin_url=person.linkedin_url,
                            name=person.name,
                            location=person.location,
                            current_job_title=person.current_job_title,
                            current_company=person.current_company,
                            about=person.about,
                            photo_path=person.photo_path,
                            first_scraped_at=person.first_scraped_at or datetime.now(),
                            last_scraped_at=person.last_scraped_at or datetime.now(),
                            scrape_count=person.scrape_count or 1,
                            is_active=True,
                        )
                        out_session.add(new_person)
                        out_session.flush()

                        # Copy experiences
                        for exp in person.experiences:
                            new_exp = Experience(
                                person_id=new_person.id,
                                position_title=exp.position_title,
                                company_name=exp.company_name,
                                location=exp.location,
                                from_date=exp.from_date,
                                to_date=exp.to_date,
                                duration=exp.duration,
                                description=exp.description,
                            )
                            out_session.add(new_exp)
                            total_experiences += 1

                        # Copy educations
                        for edu in person.educations:
                            new_edu = Education(
                                person_id=new_person.id,
                                institution_name=edu.institution_name,
                                degree=edu.degree,
                                field_of_study=edu.field_of_study,
                                from_date=edu.from_date,
                                to_date=edu.to_date,
                                description=edu.description,
                            )
                            out_session.add(new_edu)
                            total_educations += 1

                        out_session.commit()
                        new_profiles += 1

                    # Copy photo file if exists
                    if person.photo_path:
                        src_photo = os.path.join(src_dir, '..', person.photo_path)
                        if not os.path.isabs(src_photo):
                            src_photo = os.path.normpath(src_photo)
                        dst_photo = os.path.join(
                            os.path.dirname(os.path.abspath(output_path)),
                            '..',
                            person.photo_path,
                        )
                        dst_photo = os.path.normpath(dst_photo)

                        if os.path.exists(src_photo) and not os.path.exists(dst_photo):
                            os.makedirs(os.path.dirname(dst_photo), exist_ok=True)
                            shutil.copy2(src_photo, dst_photo)
                            photos_copied += 1

                except Exception as e:
                    out_session.rollback()
                    logger.warning(f"Error merging profile {person.linkedin_url}: {e}")
                finally:
                    out_session.close()

            src_session.close()

        except Exception as e:
            print(f"  ERROR: Failed to read {src_path}: {e}")
            logger.exception(f"Error reading source database: {src_path}")

    # Summary
    print("\n" + "=" * 60)
    print("MERGE SUMMARY")
    print("=" * 60)
    print(f"  Source databases:    {len(valid_sources)}")
    print(f"  Total profiles:     {total_profiles}")
    print(f"  New profiles:       {new_profiles}")
    print(f"  Updated (newer):    {updated_profiles}")
    print(f"  Skipped (older):    {skipped_profiles}")
    print(f"  Experiences added:  {total_experiences}")
    print(f"  Educations added:   {total_educations}")
    print(f"  Photos copied:      {photos_copied}")
    print(f"\n  Output: {output_path}")

    # Show final stats
    final_session = output_db.get_session()
    try:
        final_count = final_session.query(Person).filter(Person.is_active == True).count()
        print(f"  Total profiles in merged DB: {final_count}")
    finally:
        final_session.close()

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple LinkedIn scraper databases into one."
    )
    parser.add_argument(
        'databases',
        nargs='+',
        help="Paths to source .db files to merge",
    )
    parser.add_argument(
        '-o', '--output',
        default=DEFAULT_OUTPUT,
        help=f"Output database path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        '--photos-dir',
        default=DEFAULT_PHOTOS_DIR,
        help=f"Directory for consolidated photos (default: {DEFAULT_PHOTOS_DIR})",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("DATABASE MERGE TOOL")
    print("=" * 60)

    merge_databases(args.databases, args.output, args.photos_dir)


if __name__ == '__main__':
    main()
