import random
import mysql.connector
from faker import Faker

config = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'students',
}

fake = Faker('ru_RU')

realistic_courses = [
    ("Базы данных и SQL",
     "Изучение реляционных баз данных, проектирование схем, написание сложных SQL-запросов и оптимизация индексов."),
    ("Веб-разработка на Python",
     "Создание современных веб-приложений с использованием фреймворков Django и FastAPI, работа с API."),
    ("Frontend-разработчик",
     "Освоение HTML5, CSS3, JavaScript и создание интерактивных интерфейсов на библиотеке React."),
    ("Основы Data Science",
     "Анализ данных, визуализация, работа с библиотеками Pandas, NumPy, Matplotlib и базовое машинное обучение."),
    ("Тестирование ПО (QA)",
     "Ручное и автоматизированное тестирование веб- и мобильных приложений, написание тест-кейсов и баг-репортов."),
    ("Разработка на С++",
     "Глубокое изучение синтаксиса C++, управление памятью, объектно-ориентированное программирование и алгоритмы."),
    ("Мобильная разработка",
     "Создание нативных мобильных приложений для платформ iOS and Android с использованием Flutter и Dart."),
    ("DevOps-инженер",
     "Автоматизация развертывания приложений, настройка CI/CD процессов, работа с Docker, Kubernetes и Linux."),
    ("Информационная безопасность",
     "Основы защиты компьютерных систем, сетей, поиск уязвимостей и основы этичного хакинга."),
    ("Дизайн интерфейсов UI/UX",
     "Проектирование пользовательского опыта, создание интерактивных прототипов веб-сайтов и приложений в Figma."),
    ("Системный анализ",
     "Сбор и анализ требований к программному обеспечению, моделирование бизнес-процессов с помощью UML и BPMN."),
    ("Управление IT-проектами",
     "Методологии разработки Agile, Scrum, Kanban, управление командой разработки и планирование спринтов.")
]

try:
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()
    print("Успешное подключение к базе данных.")

    # ==========================================
    # 0. ПОЛНАЯ ОЧИСТКА ВСЕХ ТАБЛИЦ
    # ==========================================
    print("Очистка старых данных...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("TRUNCATE TABLE `student_cards`;")
    cursor.execute("TRUNCATE TABLE `students_courses`;")
    cursor.execute("TRUNCATE TABLE `students`;")
    cursor.execute("TRUNCATE TABLE `groups`;")
    cursor.execute("TRUNCATE TABLE `courses`;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    # ==========================================
    # 1. ЗАПОЛНЕНИЕ ТАБЛИЦЫ `courses`
    # ==========================================
    print("Добавление курсов с описаниями...")
    insert_course_query = "INSERT INTO `courses` (name, price, description) VALUES (%s, %s, %s)"
    course_data = []
    for name, desc in realistic_courses:
        price = round(random.uniform(45.00, 145.00), 2)
        course_data.append((name, price, desc))
    cursor.executemany(insert_course_query, course_data)

    # ИСПРАВЛЕНИЕ: Достаем именно число из кортежа row[0]
    cursor.execute("SELECT course_id FROM `courses`")
    course_ids = [row[0] for row in cursor.fetchall()]

    # ==========================================
    # 2. ЗАПОЛНЕНИЕ ТАБЛИЦЫ `groups`
    # ==========================================
    print("Создание учебных групп...")
    groups_list = ['ИВТ-21', 'ЭК-22', 'ЮР-23', 'ПИ-20', 'БИ-24', 'ФИЗ-21', 'МАТ-22', 'ИСТ-23', 'ХИМ-24', 'БИО-20']
    insert_group_query = "INSERT INTO `groups` (name) VALUES (%s)"
    group_data = [(name,) for name in groups_list]
    cursor.executemany(insert_group_query, group_data)

    # ИСПРАВЛЕНИЕ: Достаем именно число из кортежа row[0]
    cursor.execute("SELECT group_id FROM `groups`")
    group_ids = [row[0] for row in cursor.fetchall()]

    # ==========================================
    # 3. ЗАПОЛНЕНИЕ ТАБЛИЦЫ `students` (1000 записей)
    # ==========================================
    print("Генерация 1000 студентов...")
    insert_student_query = "INSERT INTO `students` (name, group_id, email, age) VALUES (%s, %s, %s, %s)"

    students_data = []
    num_students = 1000

    for i in range(num_students):
        name = fake.unique.name() if i < 500 else fake.name()
        group_id = random.choice(group_ids) if group_ids else None
        email = f"student_id_{i + 1}@example.com"
        age = random.randint(16, 35)
        students_data.append((name, group_id, email, age))

    cursor.executemany(insert_student_query, students_data)

    # ИСПРАВЛЕНИЕ: Достаем именно число из кортежа row[0]
    cursor.execute("SELECT student_id FROM `students`")
    student_ids = [row[0] for row in cursor.fetchall()]

    # ==========================================
    # 4. ЗАПОЛНЕНИЕ ТАБЛИЦЫ `student_cards`
    # ==========================================
    print("Выдача студенческих карт...")
    insert_card_query = "INSERT INTO `student_cards` (card_number, issue_date, student_id) VALUES (%s, %s, %s)"
    cards_data = []
    card_numbers = random.sample(range(100000, 999999), num_students)

    for idx, s_id in enumerate(student_ids):
        card_num = f"ST-{card_numbers[idx]}"
        issue_date = fake.date_between(start_date='-2y', end_date='today')
        cards_data.append((card_num, issue_date, s_id))

    cursor.executemany(insert_card_query, cards_data)

    # ==========================================
    # 5. ЗАПОЛНЕНИЕ ТАБЛИЦЫ `students_courses`
    # ==========================================
    print("Запись студентов на курсы...")
    insert_sc_query = "INSERT INTO `students_courses` (student_id, course_id, enrolled_at) VALUES (%s, %s, %s)"
    sc_data = []

    for s_id in student_ids:
        num_courses_for_student = random.randint(1, min(2, len(course_ids)))
        chosen_courses = random.sample(course_ids, num_courses_for_student)

        for c_id in chosen_courses:
            enrolled_at = fake.date_time_between(start_date='-1y', end_date='now')
            sc_data.append((s_id, c_id, enrolled_at))

    cursor.executemany(insert_sc_query, sc_data)

    connection.commit()
    print("\n[УСПЕХ] Вся база данных успешно заполнена связными синтетическими данными!")
    print(f"Добавлено: {len(realistic_courses)} курсов, {len(groups_list)} групп, {num_students} студентов и карт.")

except mysql.connector.Error as err:
    print(f"\n[ОШИБКА] Произошел сбой при работе с MySQL: {err}")
    if 'connection' in locals():
        connection.rollback()
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
        print("Соединение с БД закрыто.")
