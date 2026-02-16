"""Tests for Flask web application routes and API endpoints."""

import json


class TestPages:

    def test_index_page(self, flask_client):
        resp = flask_client.get('/')
        assert resp.status_code == 200

    def test_profiles_page(self, flask_client):
        resp = flask_client.get('/profiles')
        assert resp.status_code == 200

    def test_profile_detail_found(self, flask_client, populated_db):
        resp = flask_client.get(f'/profile/{populated_db[0].id}')
        assert resp.status_code == 200

    def test_profile_detail_not_found(self, flask_client):
        resp = flask_client.get('/profile/99999')
        assert resp.status_code == 404

    def test_search_empty(self, flask_client):
        resp = flask_client.get('/search')
        assert resp.status_code == 200

    def test_search_with_query(self, flask_client):
        resp = flask_client.get('/search?q=Alice')
        assert resp.status_code == 200
        assert b'Alice' in resp.data

    def test_analytics_page(self, flask_client):
        resp = flask_client.get('/analytics')
        assert resp.status_code == 200


class TestInputValidation:

    def test_search_strips_whitespace(self, flask_client):
        resp = flask_client.get('/search?q=%20%20Alice%20%20')
        assert resp.status_code == 200
        assert b'Alice' in resp.data

    def test_search_truncates_long_input(self, flask_client):
        long_query = 'A' * 500
        resp = flask_client.get(f'/search?q={long_query}')
        assert resp.status_code == 200

    def test_page_zero_clamps_to_one(self, flask_client):
        resp = flask_client.get('/profiles?page=0')
        assert resp.status_code == 200

    def test_page_negative_clamps_to_one(self, flask_client):
        resp = flask_client.get('/profiles?page=-5')
        assert resp.status_code == 200

    def test_page_too_large_clamps_to_last(self, flask_client):
        resp = flask_client.get('/profiles?page=999999')
        assert resp.status_code == 200

    def test_page_non_integer_defaults_to_one(self, flask_client):
        resp = flask_client.get('/profiles?page=abc')
        assert resp.status_code == 200

    def test_search_special_characters(self, flask_client):
        resp = flask_client.get('/search?q=<script>alert(1)</script>')
        assert resp.status_code == 200
        assert b'<script>' not in resp.data


class TestAPI:

    def test_api_stats(self, flask_client):
        resp = flask_client.get('/api/stats')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'total_persons' in data
        assert 'total_experiences' in data
        assert 'total_educations' in data
        assert 'active_persons' in data
        assert data['total_persons'] == 3

    def test_api_profile_found(self, flask_client, populated_db):
        resp = flask_client.get(f'/api/profile/{populated_db[0].id}')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['name'] == 'Alice Smith'
        assert 'experiences' in data
        assert 'educations' in data

    def test_api_profile_not_found(self, flask_client):
        resp = flask_client.get('/api/profile/99999')
        assert resp.status_code == 404


class TestActions:

    def test_delete_profile_redirects(self, flask_client, populated_db):
        resp = flask_client.post(
            f'/delete/{populated_db[0].id}',
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert '/profiles' in resp.headers['Location']

    def test_export_unsupported_format(self, flask_client):
        resp = flask_client.get('/export/xml')
        assert resp.status_code == 400
