"""Tests for database models and DatabaseManager."""

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database.models import (
    DatabaseManager,
    Person,
    Experience,
    Education,
    ProfileHistory,
)


class TestDatabaseManager:
    """Tests for DatabaseManager initialization and operations."""

    def test_create_all_tables(self, db_manager):
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        assert 'persons' in tables
        assert 'experiences' in tables
        assert 'educations' in tables
        assert 'profile_history' in tables

    def test_drop_all_tables(self, db_manager):
        db_manager.drop_all_tables()
        inspector = inspect(db_manager.engine)
        assert inspector.get_table_names() == []
        # Recreate so autouse fixture teardown doesn't fail
        db_manager.create_all_tables()

    def test_get_session(self, db_manager):
        session = db_manager.get_session()
        assert isinstance(session, Session)
        session.close()

    def test_get_stats_empty_db(self, db_manager):
        stats = db_manager.get_stats()
        assert stats['total_persons'] == 0
        assert stats['total_experiences'] == 0
        assert stats['total_educations'] == 0
        assert stats['total_history_records'] == 0
        assert stats['active_persons'] == 0

    def test_get_stats_with_data(self, db_manager):
        session = db_manager.get_session()
        person = Person(
            linkedin_url='https://linkedin.com/in/test',
            name='Test User',
            is_active=True,
        )
        session.add(person)
        session.flush()

        exp = Experience(
            person_id=person.id,
            position_title='Dev',
            company_name='Acme',
        )
        edu = Education(
            person_id=person.id,
            institution_name='MIT',
        )
        session.add_all([exp, edu])
        session.commit()
        session.close()

        stats = db_manager.get_stats()
        assert stats['total_persons'] == 1
        assert stats['total_experiences'] == 1
        assert stats['total_educations'] == 1
        assert stats['active_persons'] == 1


class TestPersonModel:
    """Tests for Person ORM model."""

    def test_repr(self, db_manager):
        person = Person(name='John', current_company='Google')
        assert "John" in repr(person)
        assert "Google" in repr(person)

    def test_relationships(self, db_manager):
        session = db_manager.get_session()
        person = Person(
            linkedin_url='https://linkedin.com/in/rel-test',
            name='Rel Test',
        )
        session.add(person)
        session.flush()

        exp = Experience(person_id=person.id, position_title='Dev', company_name='Co')
        edu = Education(person_id=person.id, institution_name='Uni')
        history = ProfileHistory(
            person_id=person.id,
            changed_field='name',
            old_value='Old',
            new_value='New',
        )
        session.add_all([exp, edu, history])
        session.commit()

        assert len(person.experiences) == 1
        assert len(person.educations) == 1
        assert len(person.history) == 1
        session.close()

    def test_cascade_delete(self, db_manager):
        session = db_manager.get_session()
        person = Person(
            linkedin_url='https://linkedin.com/in/cascade',
            name='Cascade Test',
        )
        session.add(person)
        session.flush()

        session.add(Experience(person_id=person.id, position_title='Dev', company_name='Co'))
        session.add(Education(person_id=person.id, institution_name='Uni'))
        session.add(ProfileHistory(
            person_id=person.id, changed_field='name',
            old_value='A', new_value='B',
        ))
        session.commit()

        session.delete(person)
        session.commit()

        assert session.query(Person).count() == 0
        assert session.query(Experience).count() == 0
        assert session.query(Education).count() == 0
        assert session.query(ProfileHistory).count() == 0
        session.close()


class TestExperienceModel:

    def test_repr(self, db_manager):
        exp = Experience(position_title='Engineer', company_name='Tesla')
        assert 'Engineer' in repr(exp)
        assert 'Tesla' in repr(exp)


class TestEducationModel:

    def test_repr(self, db_manager):
        edu = Education(institution_name='Harvard', degree='PhD')
        assert 'Harvard' in repr(edu)
        assert 'PhD' in repr(edu)


class TestProfileHistoryModel:

    def test_repr(self, db_manager):
        h = ProfileHistory(changed_field='location')
        assert 'location' in repr(h)
