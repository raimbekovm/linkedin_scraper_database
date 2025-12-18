"""
LinkedIn Scraper с сохранением в базу данных
Поддержка дедупликации и отслеживания изменений
"""
import time
import sys
import os

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_scraper import Person
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from database.operations import ProfileManager
from database.models import get_db_manager


def scrape_profile_to_db(profile_url, driver, pm, track_changes=True):
    """
    Скрэйпить профиль и сохранить в БД

    Args:
        profile_url: URL профиля LinkedIn
        driver: Selenium WebDriver
        pm: ProfileManager instance
        track_changes: отслеживать изменения в истории
    """
    try:
        print(f"\nСкрэйпинг: {profile_url}")

        # Скрэйпим профиль
        person = Person(profile_url, driver=driver, scrape=False)
        person.scrape(close_on_complete=False)

        # Формируем данные для сохранения
        experiences = []
        if hasattr(person, 'experiences') and person.experiences:
            for exp in person.experiences:
                experiences.append({
                    'position_title': exp.position_title,
                    'institution_name': exp.institution_name,
                    'location': exp.location,
                    'from_date': exp.from_date,
                    'to_date': exp.to_date,
                    'duration': exp.duration,
                    'description': exp.description
                })

        educations = []
        if hasattr(person, 'educations') and person.educations:
            for edu in person.educations:
                educations.append({
                    'institution_name': edu.institution_name,
                    'degree': edu.degree,
                    'from_date': edu.from_date,
                    'to_date': edu.to_date,
                    'description': edu.description
                })

        profile_data = {
            'linkedin_url': profile_url,
            'name': person.name,
            'location': getattr(person, 'location', None),
            'job_title': getattr(person, 'job_title', None),
            'company': getattr(person, 'company', None),
            'about': getattr(person, 'about', None),
            'experiences': experiences,
            'educations': educations
        }

        # Сохраняем в БД
        saved_person = pm.save_profile(profile_data, track_changes=track_changes)

        print(f"✓ Профиль сохранен в БД (ID: {saved_person.id})")
        print(f"  - Имя: {saved_person.name}")
        print(f"  - Компания: {saved_person.current_company}")
        print(f"  - Опыт: {len(experiences)} мест работы")
        print(f"  - Образование: {len(educations)} учебных заведений")
        print(f"  - Количество скрэйпов: {saved_person.scrape_count}")

        return saved_person

    except Exception as e:
        print(f"✗ Ошибка при скрэйпинге {profile_url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Главная функция для скрэйпинга профилей"""

    # Инициализируем БД
    print("="*60)
    print("ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ")
    print("="*60)

    db = get_db_manager()
    db.create_all_tables()
    pm = ProfileManager()

    stats = db.get_stats()
    print(f"\nТекущая статистика БД:")
    print(f"  - Профилей: {stats['total_persons']}")
    print(f"  - Опыт работы: {stats['total_experiences']}")
    print(f"  - Образование: {stats['total_educations']}")
    print(f"  - Записей истории: {stats['total_history_records']}")

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("\n" + "="*60)
        print("АВТОРИЗАЦИЯ В LINKEDIN")
        print("="*60)
        print("1. Залогиньтесь в LinkedIn в открывшемся браузере")
        print("2. У вас есть 60 секунд для логина")
        print("3. Скрэйпинг начнется автоматически")
        print("="*60 + "\n")

        # Открываем LinkedIn
        driver.get("https://www.linkedin.com/login")

        # Ждем 60 секунд для ручного логина
        print("Ожидание логина (60 секунд)...")
        for i in range(60, 0, -10):
            print(f"{i} секунд осталось...")
            time.sleep(10)

        # Список профилей для скрэйпинга
        profiles_to_scrape = [
            "https://www.linkedin.com/in/sultan-baisbekov-a079b4362/",
            "https://www.linkedin.com/in/nurbolot-piridinov/",
            "https://www.linkedin.com/in/amantai-akunov-52363b227/",
            "https://www.linkedin.com/in/baktygul-tazhamatova-389048208/",
        ]

        print("\n" + "="*60)
        print(f"НАЧИНАЕМ СКРЭЙПИНГ ({len(profiles_to_scrape)} профилей)")
        print("="*60)

        successful = 0
        failed = 0

        for idx, profile_url in enumerate(profiles_to_scrape, 1):
            print(f"\n[{idx}/{len(profiles_to_scrape)}] ", end="")

            result = scrape_profile_to_db(profile_url, driver, pm, track_changes=True)

            if result:
                successful += 1
            else:
                failed += 1

            # Небольшая пауза между профилями
            if idx < len(profiles_to_scrape):
                print("\nПауза 5 секунд перед следующим профилем...")
                time.sleep(5)

        # Итоговая статистика
        print("\n" + "="*60)
        print("ИТОГИ СКРЭЙПИНГА")
        print("="*60)
        print(f"✓ Успешно: {successful}")
        print(f"✗ Ошибок: {failed}")
        print(f"📊 Всего обработано: {successful + failed}")

        # Обновленная статистика БД
        stats = db.get_stats()
        print(f"\nОбновленная статистика БД:")
        print(f"  - Профилей: {stats['total_persons']}")
        print(f"  - Опыт работы: {stats['total_experiences']}")
        print(f"  - Образование: {stats['total_educations']}")
        print(f"  - Записей истории: {stats['total_history_records']}")

        print("\n" + "="*60)
        print("Браузер закроется через 10 секунд...")
        time.sleep(10)

    except Exception as e:
        print(f"\nПроизошла критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\nБраузер закрыт.")


if __name__ == "__main__":
    main()
