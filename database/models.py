"""
Database models for LinkedIn Scraper.

This module defines the SQLAlchemy ORM models for storing LinkedIn profile data
in a normalized relational database schema.
"""

from datetime import datetime
from typing import Dict, Optional
import logging

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

Base = declarative_base()


class Person(Base):
    """
    LinkedIn profile information.

    Stores core profile data including current position, location,
    and metadata about scraping history.
    """
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True)
    linkedin_url = Column(String(500), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    location = Column(String(200))
    current_job_title = Column(String(300))
    current_company = Column(String(300))
    about = Column(Text)

    first_scraped_at = Column(DateTime, default=datetime.now, nullable=False)
    last_scraped_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    scrape_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    experiences = relationship("Experience", back_populates="person", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="person", cascade="all, delete-orphan")
    history = relationship("ProfileHistory", back_populates="person", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_name_location', 'name', 'location'),
        Index('idx_company', 'current_company'),
    )

    def __repr__(self) -> str:
        return f"<Person(name='{self.name}', company='{self.current_company}')>"


class Experience(Base):
    """
    Work experience records.

    Stores employment history including position, company, dates, and description.
    """
    __tablename__ = 'experiences'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)

    position_title = Column(String(300), nullable=False)
    company_name = Column(String(300), nullable=False, index=True)
    location = Column(String(200))
    from_date = Column(String(50))
    to_date = Column(String(50))
    duration = Column(String(100))
    description = Column(Text)

    created_at = Column(DateTime, default=datetime.now)

    person = relationship("Person", back_populates="experiences")

    __table_args__ = (
        Index('idx_person_company', 'person_id', 'company_name'),
    )

    def __repr__(self) -> str:
        return f"<Experience(title='{self.position_title}', company='{self.company_name}')>"


class Education(Base):
    """
    Education records.

    Stores academic background including institution, degree, and dates.
    """
    __tablename__ = 'educations'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)

    institution_name = Column(String(300), nullable=False, index=True)
    degree = Column(String(300))
    field_of_study = Column(String(300))
    from_date = Column(String(50))
    to_date = Column(String(50))
    description = Column(Text)

    created_at = Column(DateTime, default=datetime.now)

    person = relationship("Person", back_populates="educations")

    def __repr__(self) -> str:
        return f"<Education(institution='{self.institution_name}', degree='{self.degree}')>"


class ProfileHistory(Base):
    """
    Audit trail for profile changes.

    Tracks all modifications to profile data for change history and analysis.
    """
    __tablename__ = 'profile_history'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)

    changed_field = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    person = relationship("Person", back_populates="history")

    def __repr__(self) -> str:
        return f"<ProfileHistory(field='{self.changed_field}', changed_at='{self.changed_at}')>"


class DatabaseManager:
    """
    Database connection and session management.

    Provides centralized database operations including table creation,
    session management, and basic statistics.

    Attributes:
        engine: SQLAlchemy engine instance
        Session: SQLAlchemy session factory
    """

    def __init__(self, db_url: str = 'sqlite:///data/linkedin_profiles.db'):
        """
        Initialize database manager.

        Args:
            db_url: Database connection URL (default: SQLite in data directory)
        """
        self.engine: Engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Database manager initialized with URL: {db_url}")

    def create_all_tables(self) -> None:
        """Create all database tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created successfully")

    def drop_all_tables(self) -> None:
        """
        Drop all database tables.

        Warning: This is a destructive operation and cannot be undone.
        """
        Base.metadata.drop_all(self.engine)
        logger.warning("All database tables dropped")

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session instance
        """
        return self.Session()

    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dictionary containing counts for various entities
        """
        session = self.get_session()
        try:
            stats = {
                'total_persons': session.query(Person).count(),
                'total_experiences': session.query(Experience).count(),
                'total_educations': session.query(Education).count(),
                'total_history_records': session.query(ProfileHistory).count(),
                'active_persons': session.query(Person).filter(Person.is_active == True).count(),
            }
            return stats
        finally:
            session.close()


def get_db_manager(db_url: Optional[str] = None) -> DatabaseManager:
    """
    Factory function for DatabaseManager instances.

    Args:
        db_url: Optional custom database URL

    Returns:
        DatabaseManager instance
    """
    return DatabaseManager(db_url) if db_url else DatabaseManager()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager()
    db.create_all_tables()
    stats = db.get_stats()
    logger.info(f"Database statistics: {stats}")
