"""
Database operations for profile management and analytics.

This module provides high-level interfaces for CRUD operations on LinkedIn profiles,
including deduplication, change tracking, and analytics queries.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from database.models import Person, Experience, Education, ProfileHistory, get_db_manager

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manager for LinkedIn profile CRUD operations.

    Handles profile creation, updates, deduplication, and search operations
    with optional change tracking for audit trails.
    """

    def __init__(self) -> None:
        """Initialize ProfileManager with database connection."""
        self.db = get_db_manager()

    def save_profile(self, person_data: Dict, track_changes: bool = True) -> Person:
        """
        Save or update profile with automatic deduplication.

        Args:
            person_data: Dictionary containing profile data with required 'linkedin_url' key
            track_changes: Whether to track field changes in profile history

        Returns:
            Person: Saved or updated Person object

        Raises:
            ValueError: If linkedin_url is missing from person_data
        """
        session = self.db.get_session()
        try:
            linkedin_url = person_data.get('linkedin_url')
            if not linkedin_url:
                raise ValueError("linkedin_url is required")

            # Проверяем, существует ли профиль (дедупликация)
            existing_person = session.query(Person).filter(
                Person.linkedin_url == linkedin_url
            ).first()

            if existing_person:
                updated_person = self._update_profile(
                    session, existing_person, person_data, track_changes
                )
                session.commit()
                logger.info(f"Profile updated: {updated_person.name}")
                return updated_person
            else:
                new_person = self._create_profile(session, person_data)
                session.commit()
                logger.info(f"New profile created: {new_person.name}")
                return new_person

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving profile: {e}")
            raise
        finally:
            session.close()

    def _create_profile(self, session, data: Dict) -> Person:
        """
        Create new profile with associated experiences and educations.

        Args:
            session: SQLAlchemy session
            data: Profile data dictionary

        Returns:
            Person: Newly created Person object
        """
        person = Person(
            linkedin_url=data['linkedin_url'],
            name=data.get('name', 'Unknown'),
            location=data.get('location'),
            current_job_title=data.get('job_title'),
            current_company=data.get('company'),
            about=data.get('about'),
            first_scraped_at=datetime.now(),
            last_scraped_at=datetime.now(),
            scrape_count=1
        )
        session.add(person)
        session.flush()  # Получить ID

        # Добавляем опыт работы
        if data.get('experiences'):
            for exp_data in data['experiences']:
                exp = Experience(
                    person_id=person.id,
                    position_title=exp_data.get('position_title', ''),
                    company_name=exp_data.get('institution_name', ''),
                    location=exp_data.get('location'),
                    from_date=exp_data.get('from_date'),
                    to_date=exp_data.get('to_date'),
                    duration=exp_data.get('duration'),
                    description=exp_data.get('description')
                )
                session.add(exp)

        # Добавляем образование
        if data.get('educations'):
            for edu_data in data['educations']:
                edu = Education(
                    person_id=person.id,
                    institution_name=edu_data.get('institution_name', ''),
                    degree=edu_data.get('degree'),
                    field_of_study=None,
                    from_date=edu_data.get('from_date'),
                    to_date=edu_data.get('to_date'),
                    description=edu_data.get('description')
                )
                session.add(edu)

        return person

    def _update_profile(self, session, person: Person, data: Dict, track_changes: bool) -> Person:
        """
        Update existing profile with new data and optionally track changes.

        Args:
            session: SQLAlchemy session
            person: Existing Person object to update
            data: New profile data
            track_changes: Whether to record changes in profile_history

        Returns:
            Person: Updated Person object
        """
        changes = []

        # Проверяем изменения в основных полях
        fields_to_check = {
            'name': data.get('name'),
            'location': data.get('location'),
            'current_job_title': data.get('job_title'),
            'current_company': data.get('company'),
            'about': data.get('about')
        }

        for field, new_value in fields_to_check.items():
            if new_value and getattr(person, field) != new_value:
                old_value = getattr(person, field)
                setattr(person, field, new_value)
                changes.append((field, old_value, new_value))

        # Сохраняем историю изменений
        if track_changes and changes:
            for field, old_val, new_val in changes:
                history = ProfileHistory(
                    person_id=person.id,
                    changed_field=field,
                    old_value=str(old_val) if old_val else None,
                    new_value=str(new_val) if new_val else None,
                    changed_at=datetime.now()
                )
                session.add(history)

        # Обновляем метаданные
        person.last_scraped_at = datetime.now()
        person.scrape_count += 1

        # Обновляем опыт работы (удаляем старые и добавляем новые)
        if data.get('experiences'):
            # Удаляем старые
            session.query(Experience).filter(Experience.person_id == person.id).delete()
            # Добавляем новые
            for exp_data in data['experiences']:
                exp = Experience(
                    person_id=person.id,
                    position_title=exp_data.get('position_title', ''),
                    company_name=exp_data.get('institution_name', ''),
                    location=exp_data.get('location'),
                    from_date=exp_data.get('from_date'),
                    to_date=exp_data.get('to_date'),
                    duration=exp_data.get('duration'),
                    description=exp_data.get('description')
                )
                session.add(exp)

        # Обновляем образование
        if data.get('educations'):
            session.query(Education).filter(Education.person_id == person.id).delete()
            for edu_data in data['educations']:
                edu = Education(
                    person_id=person.id,
                    institution_name=edu_data.get('institution_name', ''),
                    degree=edu_data.get('degree'),
                    from_date=edu_data.get('from_date'),
                    to_date=edu_data.get('to_date'),
                    description=edu_data.get('description')
                )
                session.add(edu)

        return person

    def get_profile_by_url(self, linkedin_url: str) -> Optional[Person]:
        """
        Retrieve profile by LinkedIn URL.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            Person object if found, None otherwise
        """
        session = self.db.get_session()
        try:
            return session.query(Person).filter(
                Person.linkedin_url == linkedin_url
            ).first()
        finally:
            session.close()

    def search_profiles(
        self,
        query: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50
    ) -> List[Person]:
        """
        Search profiles by multiple criteria.

        Args:
            query: Search term for profile names
            company: Filter by company name
            location: Filter by location
            limit: Maximum number of results to return

        Returns:
            List of Person objects matching the criteria
        """
        session = self.db.get_session()
        try:
            q = session.query(Person).filter(Person.is_active == True)

            if query:
                q = q.filter(Person.name.ilike(f'%{query}%'))
            if company:
                q = q.filter(Person.current_company.ilike(f'%{company}%'))
            if location:
                q = q.filter(Person.location.ilike(f'%{location}%'))

            return q.limit(limit).all()
        finally:
            session.close()

    def get_profile_history(self, person_id: int) -> List[ProfileHistory]:
        """
        Get change history for a profile.

        Args:
            person_id: Profile ID

        Returns:
            List of ProfileHistory records ordered by change date (newest first)
        """
        session = self.db.get_session()
        try:
            return session.query(ProfileHistory).filter(
                ProfileHistory.person_id == person_id
            ).order_by(ProfileHistory.changed_at.desc()).all()
        finally:
            session.close()

    def get_all_profiles(self, active_only: bool = True) -> List[Person]:
        """
        Retrieve all profiles with eager loading of relationships.

        Args:
            active_only: If True, return only active (non-deleted) profiles

        Returns:
            List of Person objects with experiences and educations loaded
        """
        session = self.db.get_session()
        try:
            q = session.query(Person).options(
                joinedload(Person.experiences),
                joinedload(Person.educations)
            )
            if active_only:
                q = q.filter(Person.is_active == True)
            profiles = q.all()
            session.expunge_all()
            return profiles
        finally:
            session.close()

    def delete_profile(self, person_id: int, soft_delete: bool = True) -> None:
        """
        Delete or deactivate a profile.

        Args:
            person_id: Profile ID to delete
            soft_delete: If True, mark as inactive; if False, permanently delete

        Raises:
            None: Logs warning if profile not found
        """
        session = self.db.get_session()
        try:
            person = session.query(Person).get(person_id)
            if person:
                if soft_delete:
                    person.is_active = False
                    session.commit()
                    logger.info(f"Profile deactivated: {person.name}")
                else:
                    session.delete(person)
                    session.commit()
                    logger.info(f"Profile permanently deleted: {person.name}")
            else:
                logger.warning(f"Profile with ID {person_id} not found")
        finally:
            session.close()


class AnalyticsManager:
    """
    Manager for analytics and aggregation queries.

    Provides methods for retrieving statistics about profiles,
    companies, locations, and educational institutions.
    """

    def __init__(self) -> None:
        """Initialize AnalyticsManager with database connection."""
        self.db = get_db_manager()

    def get_top_companies(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top companies by profile count.

        Args:
            limit: Maximum number of companies to return

        Returns:
            List of tuples (company_name, profile_count)
        """
        session = self.db.get_session()
        try:
            return session.query(
                Person.current_company,
                func.count(Person.id).label('count')
            ).filter(
                Person.is_active == True,
                Person.current_company != None
            ).group_by(
                Person.current_company
            ).order_by(
                func.count(Person.id).desc()
            ).limit(limit).all()
        finally:
            session.close()

    def get_top_locations(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top locations by profile count.

        Args:
            limit: Maximum number of locations to return

        Returns:
            List of tuples (location, profile_count)
        """
        session = self.db.get_session()
        try:
            return session.query(
                Person.location,
                func.count(Person.id).label('count')
            ).filter(
                Person.is_active == True,
                Person.location != None
            ).group_by(
                Person.location
            ).order_by(
                func.count(Person.id).desc()
            ).limit(limit).all()
        finally:
            session.close()

    def get_top_positions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top job positions by profile count.

        Args:
            limit: Maximum number of positions to return

        Returns:
            List of tuples (job_title, profile_count)
        """
        session = self.db.get_session()
        try:
            return session.query(
                Person.current_job_title,
                func.count(Person.id).label('count')
            ).filter(
                Person.is_active == True,
                Person.current_job_title != None
            ).group_by(
                Person.current_job_title
            ).order_by(
                func.count(Person.id).desc()
            ).limit(limit).all()
        finally:
            session.close()

    def get_education_stats(self) -> List[Tuple[str, int]]:
        """
        Get statistics on educational institutions.

        Returns:
            List of tuples (institution_name, count) ordered by frequency
        """
        session = self.db.get_session()
        try:
            return session.query(
                Education.institution_name,
                func.count(Education.id).label('count')
            ).group_by(
                Education.institution_name
            ).order_by(
                func.count(Education.id).desc()
            ).limit(10).all()
        finally:
            session.close()


if __name__ == "__main__":
    # Тестирование
    pm = ProfileManager()
    am = AnalyticsManager()

    print("Менеджер профилей и аналитики готов к работе!")
