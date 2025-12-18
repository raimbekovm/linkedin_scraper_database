"""
Flask web application for LinkedIn Scraper Database.

Provides dashboard, search, profile viewing, analytics, and data export
capabilities through a web interface.
"""

import sys
import os
import logging

sys.path.insert(0, '/Users/admin/PycharmProjects/linkedin_scraper')

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from database.models import get_db_manager
from database.operations import ProfileManager, AnalyticsManager
from database.export import DataExporter

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize managers
db = get_db_manager()
pm = ProfileManager()
am = AnalyticsManager()
exporter = DataExporter()


@app.route('/')
def index():
    """
    Dashboard home page.

    Displays database statistics, top companies, locations, and positions.
    """
    stats = db.get_stats()
    top_companies = am.get_top_companies(limit=5)
    top_locations = am.get_top_locations(limit=5)
    top_positions = am.get_top_positions(limit=5)

    return render_template('index.html',
                           stats=stats,
                           top_companies=top_companies,
                           top_locations=top_locations,
                           top_positions=top_positions)


@app.route('/profiles')
def profiles():
    """
    Display paginated list of all profiles.

    Supports pagination with 20 profiles per page.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20

    all_profiles = pm.get_all_profiles(active_only=True)

    # Простая пагинация
    start = (page - 1) * per_page
    end = start + per_page
    profiles_page = all_profiles[start:end]

    total_pages = (len(all_profiles) + per_page - 1) // per_page

    return render_template('profiles.html',
                           profiles=profiles_page,
                           page=page,
                           total_pages=total_pages,
                           total_profiles=len(all_profiles))


@app.route('/profile/<int:profile_id>')
def profile_detail(profile_id):
    """
    Display detailed profile information.

    Shows full profile data including experiences, educations, and change history.
    """
    session = db.get_session()
    try:
        from database.models import Person
        person = session.query(Person).get(profile_id)

        if not person:
            return "Профиль не найден", 404

        # История изменений
        history = pm.get_profile_history(profile_id)

        return render_template('profile_detail.html',
                               person=person,
                               history=history)
    finally:
        session.close()


@app.route('/search')
def search():
    """
    Search profiles by name, company, or location.

    Supports multi-field filtering with up to 100 results.
    """
    query = request.args.get('q', '')
    company = request.args.get('company', '')
    location = request.args.get('location', '')

    results = []
    if query or company or location:
        results = pm.search_profiles(
            query=query if query else None,
            company=company if company else None,
            location=location if location else None,
            limit=100
        )

    return render_template('search.html',
                           results=results,
                           query=query,
                           company=company,
                           location=location)


@app.route('/analytics')
def analytics():
    """
    Analytics dashboard.

    Displays top companies, locations, positions, and education statistics.
    """
    top_companies = am.get_top_companies(limit=10)
    top_locations = am.get_top_locations(limit=10)
    top_positions = am.get_top_positions(limit=10)
    education_stats = am.get_education_stats()

    return render_template('analytics.html',
                           top_companies=top_companies,
                           top_locations=top_locations,
                           top_positions=top_positions,
                           education_stats=education_stats)


@app.route('/export/<format>')
def export_data(format):
    """
    Export data in various formats.

    Supports JSON, CSV, and Excel exports of all profiles.
    """
    try:
        if format == 'json':
            filename = 'export.json'
            exporter.export_to_json(filename)
            return send_file(f'../{filename}', as_attachment=True)

        elif format == 'csv':
            filename = 'export.csv'
            exporter.export_to_csv(filename)
            return send_file(f'../{filename}', as_attachment=True)

        elif format == 'excel':
            filename = 'export.xlsx'
            exporter.export_to_excel(filename)
            return send_file(f'../{filename}', as_attachment=True)

        else:
            return jsonify({'error': 'Unsupported format'}), 400

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """
    REST API endpoint for database statistics.

    Returns JSON with counts of persons, experiences, educations, and history records.
    """
    stats = db.get_stats()
    return jsonify(stats)


@app.route('/api/profile/<int:profile_id>')
def api_profile(profile_id):
    """
    REST API endpoint for profile data.

    Returns complete profile information including experiences and educations.
    """
    session = db.get_session()
    try:
        from database.models import Person
        person = session.query(Person).get(profile_id)

        if not person:
            return jsonify({'error': 'Profile not found'}), 404

        data = {
            'id': person.id,
            'name': person.name,
            'linkedin_url': person.linkedin_url,
            'location': person.location,
            'current_job_title': person.current_job_title,
            'current_company': person.current_company,
            'about': person.about,
            'scrape_count': person.scrape_count,
            'experiences': [
                {
                    'position_title': exp.position_title,
                    'company_name': exp.company_name,
                    'from_date': exp.from_date,
                    'to_date': exp.to_date
                }
                for exp in person.experiences
            ],
            'educations': [
                {
                    'institution_name': edu.institution_name,
                    'degree': edu.degree
                }
                for edu in person.educations
            ]
        }

        return jsonify(data)
    finally:
        session.close()


@app.route('/delete/<int:profile_id>', methods=['POST'])
def delete_profile(profile_id):
    """
    Soft delete a profile.

    Marks profile as inactive rather than permanently deleting.
    """
    try:
        pm.delete_profile(profile_id, soft_delete=True)
        return redirect(url_for('profiles'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Create tables if they don't exist
    db.create_all_tables()

    print("\n" + "="*60)
    print("LinkedIn Scraper Database - Web Interface")
    print("="*60)
    print("\nServer running at: http://127.0.0.1:8080")
    print("\nAvailable pages:")
    print("  - http://127.0.0.1:8080/ - Dashboard")
    print("  - http://127.0.0.1:8080/profiles - All profiles")
    print("  - http://127.0.0.1:8080/search - Search")
    print("  - http://127.0.0.1:8080/analytics - Analytics")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=8080)
