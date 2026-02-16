"""
Shared pytest fixtures for LinkedIn Scraper tests.

All tests use an in-memory SQLite database to ensure isolation
from the real database and fast execution.
"""

import sys
import os
from unittest.mock import patch

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.models import DatabaseManager


@pytest.fixture(autouse=True)
def db_manager():
    """Create a fresh in-memory database for each test.

    Patches get_db_manager in all modules so that ProfileManager,
    AnalyticsManager, DataExporter, and Flask app all use the test DB.
    """
    manager = DatabaseManager('sqlite:///:memory:')
    manager.create_all_tables()

    with patch('database.models.get_db_manager', return_value=manager), \
         patch('database.operations.get_db_manager', return_value=manager), \
         patch('database.export.get_db_manager', return_value=manager):
        yield manager


@pytest.fixture
def pm(db_manager):
    """ProfileManager connected to the test database."""
    from database.operations import ProfileManager
    manager = ProfileManager()
    return manager


@pytest.fixture
def am(db_manager):
    """AnalyticsManager connected to the test database."""
    from database.operations import AnalyticsManager
    manager = AnalyticsManager()
    return manager


@pytest.fixture
def sample_profile_data():
    """Sample profile data dict for creating test profiles."""
    return {
        'linkedin_url': 'https://linkedin.com/in/john-doe',
        'name': 'John Doe',
        'location': 'San Francisco, CA',
        'job_title': 'Software Engineer',
        'company': 'Google',
        'about': 'Experienced software engineer.',
        'experiences': [
            {
                'position_title': 'Software Engineer',
                'institution_name': 'Google',
                'location': 'San Francisco, CA',
                'from_date': '2020-01',
                'to_date': 'Present',
                'duration': '4 years',
                'description': 'Backend development',
            },
            {
                'position_title': 'Junior Developer',
                'institution_name': 'Startup Inc',
                'location': 'New York, NY',
                'from_date': '2018-01',
                'to_date': '2019-12',
                'duration': '2 years',
                'description': 'Full-stack development',
            },
        ],
        'educations': [
            {
                'institution_name': 'MIT',
                'degree': 'B.S. Computer Science',
                'from_date': '2014',
                'to_date': '2018',
                'description': None,
            },
        ],
    }


@pytest.fixture
def populated_db(pm):
    """Insert 3 profiles into the test DB for search/analytics tests."""
    profiles = [
        {
            'linkedin_url': 'https://linkedin.com/in/alice',
            'name': 'Alice Smith',
            'location': 'Bishkek, Kyrgyzstan',
            'job_title': 'Data Analyst',
            'company': 'Google',
            'about': 'Data specialist',
            'experiences': [
                {
                    'position_title': 'Data Analyst',
                    'institution_name': 'Google',
                    'from_date': '2021-01',
                    'to_date': 'Present',
                },
            ],
            'educations': [
                {
                    'institution_name': 'AUCA',
                    'degree': 'B.A. Economics',
                },
            ],
        },
        {
            'linkedin_url': 'https://linkedin.com/in/bob',
            'name': 'Bob Johnson',
            'location': 'Bishkek, Kyrgyzstan',
            'job_title': 'Backend Developer',
            'company': 'Google',
            'about': 'Python developer',
            'experiences': [
                {
                    'position_title': 'Backend Developer',
                    'institution_name': 'Google',
                    'from_date': '2020-06',
                    'to_date': 'Present',
                },
            ],
            'educations': [
                {
                    'institution_name': 'AUCA',
                    'degree': 'B.S. Computer Science',
                },
            ],
        },
        {
            'linkedin_url': 'https://linkedin.com/in/carol',
            'name': 'Carol Williams',
            'location': 'Almaty, Kazakhstan',
            'job_title': 'Product Manager',
            'company': 'Meta',
            'about': 'PM with 5 years experience',
            'experiences': [
                {
                    'position_title': 'Product Manager',
                    'institution_name': 'Meta',
                    'from_date': '2019-03',
                    'to_date': 'Present',
                },
            ],
            'educations': [
                {
                    'institution_name': 'Stanford',
                    'degree': 'MBA',
                },
            ],
        },
    ]

    saved = []
    for data in profiles:
        saved.append(pm.save_profile(data, track_changes=False))
    return saved


@pytest.fixture
def flask_client(db_manager, populated_db):
    """Flask test client with patched database."""
    import web.app as web_app

    web_app.db = db_manager
    from database.operations import ProfileManager, AnalyticsManager
    from database.export import DataExporter
    web_app.pm = ProfileManager()
    web_app.am = AnalyticsManager()
    web_app.exporter = DataExporter()

    web_app.app.config['TESTING'] = True
    with web_app.app.test_client() as client:
        yield client
