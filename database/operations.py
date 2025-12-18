"""
Операции с базой данных: сохранение, обновление, дедупликация
"""
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from database.models import Person, Experience, Education, ProfileHistory, get_db_manager


class ProfileManager:
    """Менеджер для работы с профилями LinkedIn"""

    def __init__(self):
        self.db = get_db_manager()

    def save_profile(self, person_data, track_changes=True):
        """
        Сохранить или обновить профиль с дедупликацией

        Args:
            person_data: dict с данными профиля
            track_changes: отслеживать ли изменения в истории

        Returns:
            Person объект
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
                # Обновляем существующий профиль
                updated_person = self._update_profile(
                    session, existing_person, person_data, track_changes
                )
                session.commit()
                print(f"✓ Профиль обновлен: {updated_person.name}")
                return updated_person
            else:
                # Создаем новый профиль
                new_person = self._create_profile(session, person_data)
                session.commit()
                print(f"✓ Новый профиль создан: {new_person.name}")
                return new_person

        except Exception as e:
            session.rollback()
            print(f"✗ Ошибка при сохранении профиля: {e}")
            raise
        finally:
            session.close()

    def _create_profile(self, session, data):
        """Создать новый профиль"""
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

    def _update_profile(self, session, person, data, track_changes):
        """Обновить существующий профиль"""
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

    def get_profile_by_url(self, linkedin_url):
        """Получить профиль по URL"""
        session = self.db.get_session()
        try:
            return session.query(Person).filter(
                Person.linkedin_url == linkedin_url
            ).first()
        finally:
            session.close()

    def search_profiles(self, query=None, company=None, location=None, limit=50):
        """Поиск профилей по различным критериям"""
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

    def get_profile_history(self, person_id):
        """Получить историю изменений профиля"""
        session = self.db.get_session()
        try:
            return session.query(ProfileHistory).filter(
                ProfileHistory.person_id == person_id
            ).order_by(ProfileHistory.changed_at.desc()).all()
        finally:
            session.close()

    def get_all_profiles(self, active_only=True):
        """Получить все профили"""
        from sqlalchemy.orm import joinedload
        session = self.db.get_session()
        try:
            q = session.query(Person).options(
                joinedload(Person.experiences),
                joinedload(Person.educations)
            )
            if active_only:
                q = q.filter(Person.is_active == True)
            # Используем expunge_all чтобы объекты можно было использовать вне сессии
            profiles = q.all()
            session.expunge_all()
            return profiles
        finally:
            session.close()

    def delete_profile(self, person_id, soft_delete=True):
        """Удалить профиль (мягкое или жесткое удаление)"""
        session = self.db.get_session()
        try:
            person = session.query(Person).get(person_id)
            if person:
                if soft_delete:
                    person.is_active = False
                    session.commit()
                    print(f"✓ Профиль {person.name} деактивирован")
                else:
                    session.delete(person)
                    session.commit()
                    print(f"✓ Профиль {person.name} удален")
            else:
                print(f"✗ Профиль с ID {person_id} не найден")
        finally:
            session.close()


class AnalyticsManager:
    """Менеджер для аналитики данных"""

    def __init__(self):
        self.db = get_db_manager()

    def get_top_companies(self, limit=10):
        """Топ компаний по количеству профилей"""
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

    def get_top_locations(self, limit=10):
        """Топ локаций"""
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

    def get_top_positions(self, limit=10):
        """Топ должностей"""
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

    def get_education_stats(self):
        """Статистика по образованию"""
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
