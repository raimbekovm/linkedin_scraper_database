"""Tests for ProfileManager and AnalyticsManager."""

import pytest

from database.models import Person, Experience, Education, ProfileHistory


# ---------------------------------------------------------------------------
# ProfileManager — CRUD
# ---------------------------------------------------------------------------

class TestSaveProfile:

    def test_save_new_profile(self, pm, sample_profile_data):
        person = pm.save_profile(sample_profile_data)
        assert person.name == 'John Doe'
        assert person.location == 'San Francisco, CA'
        assert person.current_job_title == 'Software Engineer'
        assert person.current_company == 'Google'
        assert person.about == 'Experienced software engineer.'
        assert person.scrape_count == 1
        assert person.is_active is True

    def test_save_profile_with_experiences(self, pm, sample_profile_data, db_manager):
        pm.save_profile(sample_profile_data)

        session = db_manager.get_session()
        exps = session.query(Experience).all()
        assert len(exps) == 2
        titles = {e.position_title for e in exps}
        assert 'Software Engineer' in titles
        assert 'Junior Developer' in titles
        session.close()

    def test_save_profile_with_educations(self, pm, sample_profile_data, db_manager):
        pm.save_profile(sample_profile_data)

        session = db_manager.get_session()
        edus = session.query(Education).all()
        assert len(edus) == 1
        assert edus[0].institution_name == 'MIT'
        assert edus[0].degree == 'B.S. Computer Science'
        session.close()

    def test_save_profile_without_url_raises(self, pm):
        with pytest.raises(ValueError, match="linkedin_url is required"):
            pm.save_profile({'name': 'No URL'})

    def test_save_profile_default_name(self, pm):
        person = pm.save_profile({
            'linkedin_url': 'https://linkedin.com/in/noname',
        })
        assert person.name == 'Unknown'


# ---------------------------------------------------------------------------
# ProfileManager — Deduplication & Update
# ---------------------------------------------------------------------------

class TestDeduplication:

    def test_duplicate_url_updates_instead_of_creating(self, pm, db_manager):
        data = {
            'linkedin_url': 'https://linkedin.com/in/dup',
            'name': 'Original Name',
            'job_title': 'Dev',
            'company': 'Co',
        }
        pm.save_profile(data, track_changes=False)
        pm.save_profile(data, track_changes=False)

        session = db_manager.get_session()
        count = session.query(Person).count()
        assert count == 1
        session.close()

    def test_update_increments_scrape_count(self, pm, db_manager):
        url = 'https://linkedin.com/in/count'
        pm.save_profile({'linkedin_url': url, 'name': 'Counter'})
        pm.save_profile({'linkedin_url': url, 'name': 'Counter'})

        session = db_manager.get_session()
        person = session.query(Person).filter_by(linkedin_url=url).first()
        assert person.scrape_count == 2
        session.close()

    def test_update_tracks_changes(self, pm, db_manager):
        url = 'https://linkedin.com/in/track'
        pm.save_profile({
            'linkedin_url': url,
            'name': 'Old Name',
            'job_title': 'Old Title',
        })
        pm.save_profile({
            'linkedin_url': url,
            'name': 'New Name',
            'job_title': 'New Title',
        }, track_changes=True)

        session = db_manager.get_session()
        history = session.query(ProfileHistory).all()
        changed_fields = {h.changed_field for h in history}
        assert 'name' in changed_fields
        assert 'current_job_title' in changed_fields
        session.close()

    def test_update_no_tracking(self, pm, db_manager):
        url = 'https://linkedin.com/in/notrack'
        pm.save_profile({'linkedin_url': url, 'name': 'A'})
        pm.save_profile({'linkedin_url': url, 'name': 'B'}, track_changes=False)

        session = db_manager.get_session()
        assert session.query(ProfileHistory).count() == 0
        session.close()


# ---------------------------------------------------------------------------
# ProfileManager — Retrieval & Search
# ---------------------------------------------------------------------------

class TestGetProfile:

    def test_get_profile_by_url(self, pm, sample_profile_data):
        pm.save_profile(sample_profile_data)
        person = pm.get_profile_by_url(sample_profile_data['linkedin_url'])
        assert person is not None
        assert person.name == 'John Doe'

    def test_get_profile_by_url_not_found(self, pm):
        result = pm.get_profile_by_url('https://linkedin.com/in/nonexistent')
        assert result is None


class TestSearch:

    def test_search_by_name(self, pm, populated_db):
        results = pm.search_profiles(query='Alice')
        assert len(results) == 1
        assert results[0].name == 'Alice Smith'

    def test_search_by_company(self, pm, populated_db):
        results = pm.search_profiles(company='Google')
        assert len(results) == 2

    def test_search_by_location(self, pm, populated_db):
        results = pm.search_profiles(location='Almaty')
        assert len(results) == 1
        assert results[0].name == 'Carol Williams'

    def test_search_case_insensitive(self, pm, populated_db):
        results = pm.search_profiles(query='alice')
        assert len(results) == 1

    def test_search_excludes_inactive(self, pm, populated_db):
        pm.delete_profile(populated_db[0].id, soft_delete=True)
        results = pm.search_profiles(query='Alice')
        assert len(results) == 0

    def test_search_with_limit(self, pm, populated_db):
        results = pm.search_profiles(limit=1)
        assert len(results) == 1


class TestGetAllProfiles:

    def test_active_only(self, pm, populated_db):
        pm.delete_profile(populated_db[0].id, soft_delete=True)
        active = pm.get_all_profiles(active_only=True)
        assert len(active) == 2

    def test_include_inactive(self, pm, populated_db):
        pm.delete_profile(populated_db[0].id, soft_delete=True)
        all_profiles = pm.get_all_profiles(active_only=False)
        assert len(all_profiles) == 3


# ---------------------------------------------------------------------------
# ProfileManager — Delete
# ---------------------------------------------------------------------------

class TestDelete:

    def test_soft_delete(self, pm, populated_db, db_manager):
        pm.delete_profile(populated_db[0].id, soft_delete=True)

        session = db_manager.get_session()
        person = session.query(Person).get(populated_db[0].id)
        assert person is not None
        assert person.is_active is False
        session.close()

    def test_hard_delete(self, pm, populated_db, db_manager):
        pm.delete_profile(populated_db[0].id, soft_delete=False)

        session = db_manager.get_session()
        person = session.query(Person).get(populated_db[0].id)
        assert person is None
        session.close()

    def test_delete_nonexistent_no_error(self, pm):
        pm.delete_profile(99999, soft_delete=True)


# ---------------------------------------------------------------------------
# ProfileManager — History
# ---------------------------------------------------------------------------

class TestProfileHistory:

    def test_get_profile_history(self, pm):
        url = 'https://linkedin.com/in/hist'
        pm.save_profile({'linkedin_url': url, 'name': 'V1', 'job_title': 'Job1'})
        pm.save_profile({'linkedin_url': url, 'name': 'V2', 'job_title': 'Job2'}, track_changes=True)

        person = pm.get_profile_by_url(url)
        history = pm.get_profile_history(person.id)
        assert len(history) >= 1
        # Most recent change first
        fields = [h.changed_field for h in history]
        assert 'name' in fields

    def test_history_empty_for_new_profile(self, pm, sample_profile_data):
        person = pm.save_profile(sample_profile_data)
        history = pm.get_profile_history(person.id)
        assert len(history) == 0


# ---------------------------------------------------------------------------
# AnalyticsManager
# ---------------------------------------------------------------------------

class TestAnalytics:

    def test_top_companies(self, am, populated_db):
        top = am.get_top_companies(limit=10)
        companies = {name: count for name, count in top}
        assert companies['Google'] == 2
        assert companies['Meta'] == 1

    def test_top_locations(self, am, populated_db):
        top = am.get_top_locations(limit=10)
        locations = {name: count for name, count in top}
        assert locations['Bishkek, Kyrgyzstan'] == 2
        assert locations['Almaty, Kazakhstan'] == 1

    def test_top_positions(self, am, populated_db):
        top = am.get_top_positions(limit=10)
        assert len(top) == 3  # 3 unique positions

    def test_education_stats(self, am, populated_db):
        stats = am.get_education_stats()
        institutions = {name: count for name, count in stats}
        assert institutions['AUCA'] == 2
        assert institutions['Stanford'] == 1

    def test_analytics_exclude_inactive(self, am, pm, populated_db):
        pm.delete_profile(populated_db[0].id, soft_delete=True)
        top = am.get_top_companies(limit=10)
        companies = {name: count for name, count in top}
        assert companies.get('Google', 0) == 1

    def test_top_companies_exclude_null(self, am, pm, db_manager):
        pm.save_profile({
            'linkedin_url': 'https://linkedin.com/in/nullco',
            'name': 'No Company',
            # no company
        })
        top = am.get_top_companies(limit=10)
        names = [name for name, _ in top]
        assert None not in names
