# LinkedIn Scraper Database System

Полноценная система для скрэйпинга, хранения и анализа профилей LinkedIn с использованием реляционной базы данных.

## 📋 Содержание

1. [Архитектура системы](#архитектура-системы)
2. [Структура базы данных](#структура-базы-данных)
3. [Возможности](#возможности)
4. [Установка и запуск](#установка-и-запуск)
5. [Использование](#использование)
6. [API Документация](#api-документация)
7. [Примеры SQL запросов](#примеры-sql-запросов)

---

## 🏗️ Архитектура системы

### Компоненты проекта

```
linkedin_scraper/
├── database/               # Модуль базы данных
│   ├── models.py          # SQLAlchemy модели (схема БД)
│   ├── operations.py      # CRUD операции, поиск, дедупликация
│   └── export.py          # Экспорт данных (JSON, CSV, Excel)
│
├── web/                   # Веб-интерфейс (Flask)
│   ├── app.py            # Flask приложение
│   └── templates/        # HTML шаблоны
│       ├── base.html
│       ├── index.html        (Dashboard)
│       ├── profiles.html     (Список профилей)
│       ├── profile_detail.html
│       ├── search.html
│       └── analytics.html
│
├── scrape_to_database.py  # Скрэйпер с сохранением в БД
└── linkedin_profiles.db   # SQLite база данных
```

---

## 🗄️ Структура базы данных

### ER-диаграмма

```
┌─────────────────┐
│    persons      │
├─────────────────┤
│ id (PK)         │──┐
│ linkedin_url    │  │
│ name            │  │
│ location        │  │
│ current_job_    │  │
│   title         │  │
│ current_company │  │
│ about           │  │
│ first_scraped_  │  │
│   at            │  │
│ last_scraped_at │  │
│ scrape_count    │  │
│ is_active       │  │
└─────────────────┘  │
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│ experiences  │ │ educations   │ │ profile_history  │
├──────────────┤ ├──────────────┤ ├──────────────────┤
│ id (PK)      │ │ id (PK)      │ │ id (PK)          │
│ person_id(FK)│ │ person_id(FK)│ │ person_id (FK)   │
│ position_    │ │ institution_ │ │ changed_field    │
│   title      │ │   name       │ │ old_value        │
│ company_name │ │ degree       │ │ new_value        │
│ location     │ │ from_date    │ │ changed_at       │
│ from_date    │ │ to_date      │ └──────────────────┘
│ to_date      │ │ description  │
│ duration     │ └──────────────┘
│ description  │
└──────────────┘
```

### Таблицы

#### 1. **persons** - Основная таблица профилей
- `id` (PK) - Уникальный идентификатор
- `linkedin_url` (UNIQUE) - URL профиля LinkedIn
- `name` - Имя
- `location` - Локация
- `current_job_title` - Текущая должность
- `current_company` - Текущая компания
- `about` - Раздел "О себе"
- `first_scraped_at` - Дата первого скрэйпинга
- `last_scraped_at` - Дата последнего скрэйпинга
- `scrape_count` - Количество скрэйпингов
- `is_active` - Активен ли профиль

**Индексы:**
- `linkedin_url` (уникальный)
- `name, location` (составной)
- `current_company`

#### 2. **experiences** - Опыт работы
- `id` (PK)
- `person_id` (FK → persons.id)
- `position_title` - Должность
- `company_name` - Компания
- `location` - Локация работы
- `from_date` - Дата начала
- `to_date` - Дата окончания
- `duration` - Длительность
- `description` - Описание

**Индексы:**
- `person_id, company_name`

#### 3. **educations** - Образование
- `id` (PK)
- `person_id` (FK → persons.id)
- `institution_name` - Учебное заведение
- `degree` - Степень
- `from_date` - Дата начала
- `to_date` - Дата окончания
- `description` - Описание

#### 4. **profile_history** - История изменений
- `id` (PK)
- `person_id` (FK → persons.id)
- `changed_field` - Изменённое поле
- `old_value` - Старое значение
- `new_value` - Новое значение
- `changed_at` - Дата изменения

---

## ✨ Возможности

### 1. Скрэйпинг с дедупликацией
- Автоматическое определение дубликатов по LinkedIn URL
- Обновление существующих профилей при повторном скрэйпинге
- Отслеживание изменений в истории

### 2. Веб-интерфейс (Flask)
- **Dashboard** - общая статистика, топ компании/локации
- **Список профилей** - пагинация, просмотр всех профилей
- **Детальный просмотр** - полная информация о профиле
- **Поиск** - по имени, компании, локации
- **Аналитика** - топ-10 по различным категориям

### 3. Экспорт данных
- **JSON** - для анализа в Python/R
- **CSV** - для импорта в другие системы
- **Excel** - с несколькими вкладками (профили, опыт, образование)

### 4. Аналитика
- Топ компаний по количеству профилей
- Топ локаций
- Топ должностей
- Статистика по образованию
- SQL запросы для сложной аналитики

### 5. История изменений
- Tracking изменений в профилях
- Просмотр истории обновлений

---

## 🚀 Установка и запуск

### 1. Установка зависимостей

```bash
pip install sqlalchemy flask pandas openpyxl selenium requests lxml
```

### 2. Инициализация базы данных

```bash
python database/models.py
```

### 3. Миграция данных из Excel (опционально)

```python
from database.export import DataMigrator

migrator = DataMigrator()
migrator.migrate_from_excel('linkedin_profiles.xlsx')
```

### 4. Запуск скрэйпера

```bash
python scrape_to_database.py
```

### 5. Запуск веб-интерфейса

```bash
python web/app.py
```

Откройте в браузере: http://127.0.0.1:5000

---

## 💻 Использование

### Скрэйпинг профилей

```python
from database.operations import ProfileManager
from linkedin_scraper import Person

pm = ProfileManager()

# Скрэйпить профиль
person = Person("https://linkedin.com/in/username", driver=driver)

# Сохранить в БД (с дедупликацией)
profile_data = {
    'linkedin_url': "https://linkedin.com/in/username",
    'name': person.name,
    'location': person.location,
    # ...
}

pm.save_profile(profile_data, track_changes=True)
```

### Поиск профилей

```python
# Поиск по имени
results = pm.search_profiles(query="John")

# Поиск по компании
results = pm.search_profiles(company="Google")

# Комбинированный поиск
results = pm.search_profiles(
    query="John",
    company="Google",
    location="San Francisco"
)
```

### Получение аналитики

```python
from database.operations import AnalyticsManager

am = AnalyticsManager()

# Топ компаний
top_companies = am.get_top_companies(limit=10)

# Топ локаций
top_locations = am.get_top_locations(limit=10)

# Статистика по образованию
edu_stats = am.get_education_stats()
```

### Экспорт данных

```python
from database.export import DataExporter

exporter = DataExporter()

# Экспорт в JSON
exporter.export_to_json('export.json')

# Экспорт в CSV
exporter.export_to_csv('export.csv')

# Экспорт в Excel (с вкладками)
exporter.export_to_excel('export.xlsx')
```

---

## 🔌 API Документация

### REST API Endpoints

#### GET /api/stats
Получить общую статистику БД

**Response:**
```json
{
  "total_persons": 150,
  "total_experiences": 450,
  "total_educations": 200,
  "total_history_records": 50,
  "active_persons": 148
}
```

#### GET /api/profile/<id>
Получить данные профиля по ID

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "linkedin_url": "https://...",
  "location": "San Francisco",
  "current_job_title": "Software Engineer",
  "current_company": "Google",
  "experiences": [...],
  "educations": [...]
}
```

---

## 📊 Примеры SQL запросов

### 1. Найти всех выпускников определённого университета

```sql
SELECT DISTINCT p.name, p.current_company, p.current_job_title
FROM persons p
JOIN educations e ON p.id = e.person_id
WHERE e.institution_name LIKE '%AUCA%'
ORDER BY p.name;
```

### 2. Найти людей, работавших в определённой компании

```sql
SELECT DISTINCT p.name, p.location, p.current_company
FROM persons p
JOIN experiences ex ON p.id = ex.person_id
WHERE ex.company_name LIKE '%Google%'
ORDER BY p.name;
```

### 3. Статистика по компаниям и средний опыт

```sql
SELECT
    p.current_company,
    COUNT(*) as employee_count,
    COUNT(DISTINCT ex.id) as total_experiences
FROM persons p
LEFT JOIN experiences ex ON p.id = ex.person_id
WHERE p.current_company IS NOT NULL
GROUP BY p.current_company
ORDER BY employee_count DESC
LIMIT 10;
```

### 4. Найти профили с изменениями за последний месяц

```sql
SELECT DISTINCT p.name, p.linkedin_url, ph.changed_field, ph.changed_at
FROM persons p
JOIN profile_history ph ON p.id = ph.person_id
WHERE ph.changed_at >= datetime('now', '-30 days')
ORDER BY ph.changed_at DESC;
```

### 5. Топ навыков/должностей по локациям

```sql
SELECT
    p.location,
    p.current_job_title,
    COUNT(*) as count
FROM persons p
WHERE p.location IS NOT NULL AND p.current_job_title IS NOT NULL
GROUP BY p.location, p.current_job_title
HAVING count > 1
ORDER BY p.location, count DESC;
```

---

## 📈 Расширенная аналитика

### Использование pandas для анализа

```python
import pandas as pd
from database.models import get_db_manager

db = get_db_manager()

# Загрузить все профили в DataFrame
query = "SELECT * FROM persons WHERE is_active = 1"
df = pd.read_sql_query(query, db.engine)

# Анализ
print(df.groupby('current_company').size().sort_values(ascending=False).head(10))
print(df['location'].value_counts().head(10))
```

---

## 🎓 Демонстрация навыков для курса Database

Этот проект демонстрирует следующие навыки работы с БД:

### 1. **Проектирование схемы**
- ✅ Нормализация (3NF)
- ✅ Primary Keys и Foreign Keys
- ✅ Индексы для оптимизации
- ✅ Constraints (UNIQUE, NOT NULL)

### 2. **SQL и ORM**
- ✅ SQLAlchemy ORM
- ✅ Сложные JOIN запросы
- ✅ Агрегатные функции (COUNT, GROUP BY)
- ✅ Подзапросы и фильтрация

### 3. **CRUD операции**
- ✅ Create - создание профилей
- ✅ Read - поиск и чтение
- ✅ Update - обновление профилей
- ✅ Delete - мягкое удаление

### 4. **Продвинутые техники**
- ✅ Дедупликация данных
- ✅ История изменений (Audit Trail)
- ✅ Транзакции и rollback
- ✅ Миграция данных

### 5. **Интеграция**
- ✅ REST API
- ✅ Веб-интерфейс
- ✅ Экспорт в разные форматы
- ✅ Аналитика и визуализация

---

## 📝 Лицензия

MIT License

---

## 👨‍💻 Автор

Проект создан как демонстрация навыков работы с базами данных для курса Database.
