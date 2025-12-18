"""
Модели базы данных для LinkedIn Scraper
Нормализованная схема с использованием SQLAlchemy ORM
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Person(Base):
    """Таблица профилей LinkedIn"""
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True)
    linkedin_url = Column(String(500), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    location = Column(String(200))
    current_job_title = Column(String(300))
    current_company = Column(String(300))
    about = Column(Text)

    # Метаданные
    first_scraped_at = Column(DateTime, default=datetime.now, nullable=False)
    last_scraped_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    scrape_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    # Связи
    experiences = relationship("Experience", back_populates="person", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="person", cascade="all, delete-orphan")
    history = relationship("ProfileHistory", back_populates="person", cascade="all, delete-orphan")

    # Индексы для поиска
    __table_args__ = (
        Index('idx_name_location', 'name', 'location'),
        Index('idx_company', 'current_company'),
    )

    def __repr__(self):
        return f"<Person(name='{self.name}', company='{self.current_company}')>"


class Experience(Base):
    """Таблица опыта работы"""
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

    # Метаданные
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    person = relationship("Person", back_populates="experiences")

    # Индекс для поиска по компаниям
    __table_args__ = (
        Index('idx_person_company', 'person_id', 'company_name'),
    )

    def __repr__(self):
        return f"<Experience(title='{self.position_title}', company='{self.company_name}')>"


class Education(Base):
    """Таблица образования"""
    __tablename__ = 'educations'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)

    institution_name = Column(String(300), nullable=False, index=True)
    degree = Column(String(300))
    field_of_study = Column(String(300))
    from_date = Column(String(50))
    to_date = Column(String(50))
    description = Column(Text)

    # Метаданные
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    person = relationship("Person", back_populates="educations")

    def __repr__(self):
        return f"<Education(institution='{self.institution_name}', degree='{self.degree}')>"


class ProfileHistory(Base):
    """История изменений профилей (для отслеживания обновлений)"""
    __tablename__ = 'profile_history'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)

    # Что изменилось
    changed_field = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)

    # Когда изменилось
    changed_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # Связи
    person = relationship("Person", back_populates="history")

    def __repr__(self):
        return f"<ProfileHistory(field='{self.changed_field}', changed_at='{self.changed_at}')>"


# Функции для работы с БД
class DatabaseManager:
    """Менеджер для управления базой данных"""

    def __init__(self, db_url='sqlite:///data/linkedin_profiles.db'):
        """Инициализация подключения к БД"""
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

    def create_all_tables(self):
        """Создание всех таблиц"""
        Base.metadata.create_all(self.engine)
        print("✓ Все таблицы созданы успешно")

    def drop_all_tables(self):
        """Удаление всех таблиц (осторожно!)"""
        Base.metadata.drop_all(self.engine)
        print("✓ Все таблицы удалены")

    def get_session(self):
        """Получить сессию для работы с БД"""
        return self.Session()

    def get_stats(self):
        """Получить статистику по БД"""
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


# Функции для быстрого доступа
def get_db_manager():
    """Получить менеджер БД (singleton pattern)"""
    return DatabaseManager()


if __name__ == "__main__":
    # Тестирование создания БД
    db = DatabaseManager()
    db.create_all_tables()
    print("\nСтатистика БД:", db.get_stats())
