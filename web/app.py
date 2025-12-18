"""
Flask веб-приложение для LinkedIn Scraper Database
Dashboard, поиск, просмотр профилей, аналитика
"""
import sys
sys.path.insert(0, '/Users/admin/PycharmProjects/linkedin_scraper')

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from database.models import get_db_manager
from database.operations import ProfileManager, AnalyticsManager
from database.export import DataExporter
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Инициализация менеджеров
db = get_db_manager()
pm = ProfileManager()
am = AnalyticsManager()
exporter = DataExporter()


@app.route('/')
def index():
    """Главная страница - Dashboard"""
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
    """Список всех профилей"""
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
    """Детальная информация о профиле"""
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
    """Поиск профилей"""
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
    """Страница аналитики"""
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
    """Экспорт данных в различные форматы"""
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
            return jsonify({'error': 'Неподдерживаемый формат'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API для получения статистики"""
    stats = db.get_stats()
    return jsonify(stats)


@app.route('/api/profile/<int:profile_id>')
def api_profile(profile_id):
    """API для получения данных профиля"""
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
    """Удалить профиль (мягкое удаление)"""
    try:
        pm.delete_profile(profile_id, soft_delete=True)
        return redirect(url_for('profiles'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Создаем таблицы если их нет
    db.create_all_tables()

    print("\n" + "="*60)
    print("LinkedIn Scraper Database - Web Interface")
    print("="*60)
    print("\nСервер запущен на: http://127.0.0.1:8080")
    print("\nДоступные страницы:")
    print("  - http://127.0.0.1:8080/ - Dashboard")
    print("  - http://127.0.0.1:8080/profiles - Все профили")
    print("  - http://127.0.0.1:8080/search - Поиск")
    print("  - http://127.0.0.1:8080/analytics - Аналитика")
    print("\nДля остановки нажмите Ctrl+C")
    print("="*60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=8080)
