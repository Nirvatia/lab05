import random
from decimal import Decimal

from faker import Faker
from sqlalchemy import delete, func, select

from db import SessionLocal, engine
from models import Course, Group, Student, StudentCard, StudentCourse, Students

fake = Faker("ru_RU")

# Названия курсов укорочены до 20 символов — ограничение String(20) из models.py
COURSES = [
    ("Базы данных и SQL",
     "Изучение реляционных баз данных, проектирование схем, написание сложных SQL-запросов и оптимизация индексов."),
    ("Веб-разработка",
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
     "Создание нативных мобильных приложений для платформ iOS и Android с использованием Flutter и Dart."),
    ("DevOps-инженер",
     "Автоматизация развертывания приложений, настройка CI/CD процессов, работа с Docker, Kubernetes и Linux."),
    ("Инфобезопасность",
     "Основы защиты компьютерных систем, сетей, поиск уязвимостей и основы этичного хакинга."),
    ("Дизайн UI/UX",
     "Проектирование пользовательского опыта, создание интерактивных прототипов веб-сайтов и приложений в Figma."),
    ("Системный анализ",
     "Сбор и анализ требований к программному обеспечению, моделирование бизнес-процессов с помощью UML и BPMN."),
    ("Управление проектами",
     "Методологии разработки Agile, Scrum, Kanban, управление командой разработки и планирование спринтов."),
]

GROUPS = ["ИВТ-21", "ЭК-22", "ЮР-23", "ПИ-20", "БИ-24",
          "ФИЗ-21", "МАТ-22", "ИСТ-23", "ХИМ-24", "БИО-20"]


def seed(num_students: int = 1000) -> dict:
    """Полностью перезаполняет БД тестовыми данными через ORM-объекты."""
    Students.metadata.create_all(engine)

    with SessionLocal() as session:
        for model in (StudentCourse, StudentCard, Student, Group, Course):
            session.execute(delete(model))
        session.commit()

        courses = [
            Course(name=name,
                   price=Decimal(str(round(random.uniform(45.00, 145.00), 2))),
                   description=desc)
            for name, desc in COURSES
        ]
        groups = [Group(name=name) for name in GROUPS]
        session.add_all(courses + groups)
        session.commit()

        students = [
            Student(
                name=fake.unique.name() if i < 500 else fake.name(),
                group_id=random.choice(groups).group_id,
                email=f"student_id_{i + 1}@example.com",
                age=random.randint(16, 35),
            )
            for i in range(num_students)
        ]
        session.add_all(students)
        session.commit()

        card_numbers = random.sample(range(100000, 999999), num_students)
        cards = [
            StudentCard(
                card_number=f"ST-{card_numbers[i]}",
                issue_date=fake.date_between(start_date="-2y", end_date="today"),
                student_id=student.student_id,
            )
            for i, student in enumerate(students)
        ]
        session.add_all(cards)

        enrollments = []
        for student in students:
            for course in random.sample(courses, random.randint(1, 2)):
                enrollments.append(StudentCourse(
                    student_id=student.student_id,
                    course_id=course.course_id,
                    enrolled_at=fake.date_time_between(start_date="-1y", end_date="now"),
                ))
        session.add_all(enrollments)
        session.commit()

        counts = {
            "courses": session.scalar(select(func.count()).select_from(Course)),
            "groups": session.scalar(select(func.count()).select_from(Group)),
            "students": session.scalar(select(func.count()).select_from(Student)),
            "cards": session.scalar(select(func.count()).select_from(StudentCard)),
            "enrollments": session.scalar(select(func.count()).select_from(StudentCourse)),
        }

    print("[УСПЕХ] База заполнена через ORM:")
    for table, count in counts.items():
        print(f"  {table}: {count}")
    return counts


if __name__ == "__main__":
    seed()