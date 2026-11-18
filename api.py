from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from db import engine, get_db
from models import Course, Group, Student, StudentCard, StudentCourse, Students
from seed import seed

Students.metadata.create_all(engine)

app = FastAPI(
    title="Students ORM API",
    description="Демо-панель для лабораторной работы: доступ к БД только через ORM-классы models.py",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def commit_or_400(db: Session):
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Нарушение ограничения БД: {err.orig}")


# ==========================================
# PYDANTIC-СХЕМЫ
# ==========================================
class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    group_id: int
    name: str


class GroupWithCount(GroupOut):
    students_count: int


class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    price: float = Field(default=0.0, ge=0)
    description: Optional[str] = None


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    course_id: int
    name: str
    price: float
    description: Optional[str]


class CourseWithCount(CourseOut):
    students_count: int


class CardIn(BaseModel):
    card_number: str = Field(min_length=1, max_length=20)
    student_id: int
    issue_date: Optional[date] = None


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    card_id: int
    card_number: str
    issue_date: date
    student_id: Optional[int]


class StudentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    group_id: Optional[int] = None
    email: EmailStr
    age: int = Field(ge=16, le=120)


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: int
    name: str
    group_id: Optional[int]
    email: str
    age: int
    group: Optional[GroupOut]
    card: Optional[CardOut]
    courses: List[CourseOut]


class StudentPage(BaseModel):
    items: List[StudentOut]
    total: int


class EnrollmentIn(BaseModel):
    student_id: int
    course_id: int


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: int
    course_id: int
    enrolled_at: Optional[datetime]


class StatsOut(BaseModel):
    students: int
    groups: int
    courses: int
    cards: int
    enrollments: int
    avg_age: Optional[float]


# ==========================================
# СТАТИСТИКА И ТЕСТОВЫЕ ДАННЫЕ
# ==========================================
@app.get("/api/stats", response_model=StatsOut, tags=["Stats"])
def get_stats(db: Session = Depends(get_db)):
    return StatsOut(
        students=db.scalar(select(func.count()).select_from(Student)),
        groups=db.scalar(select(func.count()).select_from(Group)),
        courses=db.scalar(select(func.count()).select_from(Course)),
        cards=db.scalar(select(func.count()).select_from(StudentCard)),
        enrollments=db.scalar(select(func.count()).select_from(StudentCourse)),
        avg_age=round(db.scalar(select(func.avg(Student.age))) or 0, 1),
    )


@app.post("/api/seed", tags=["Stats"])
def reseed(num_students: int = Query(default=1000, ge=1, le=5000)):
    """Полностью пересоздаёт тестовые данные (как fillDatabase.py, но через ORM)."""
    return seed(num_students)


# ==========================================
# СТУДЕНТЫ
# ==========================================
@app.get("/api/students", response_model=StudentPage, tags=["Students"])
def list_students(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str = "",
    group_id: Optional[int] = None,
):
    stmt = select(Student).options(
        selectinload(Student.group),
        selectinload(Student.card),
        selectinload(Student.courses),
    )
    count_stmt = select(func.count()).select_from(Student)
    if search:
        cond = or_(Student.name.like(f"%{search}%"), Student.email.like(f"%{search}%"))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if group_id is not None:
        stmt = stmt.where(Student.group_id == group_id)
        count_stmt = count_stmt.where(Student.group_id == group_id)

    items = db.scalars(stmt.order_by(Student.student_id).limit(limit).offset(offset)).all()
    return StudentPage(items=items, total=db.scalar(count_stmt))


def get_student_or_404(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    return student


@app.get("/api/students/{student_id}", response_model=StudentOut, tags=["Students"])
def read_student(student_id: int, db: Session = Depends(get_db)):
    return get_student_or_404(db, student_id)


@app.post("/api/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED, tags=["Students"])
def create_student(data: StudentIn, db: Session = Depends(get_db)):
    student = Student(**data.model_dump())
    db.add(student)
    commit_or_400(db)
    return student


@app.put("/api/students/{student_id}", response_model=StudentOut, tags=["Students"])
def update_student(student_id: int, data: StudentIn, db: Session = Depends(get_db)):
    student = get_student_or_404(db, student_id)
    for field, value in data.model_dump().items():
        setattr(student, field, value)
    commit_or_400(db)
    return student


@app.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = get_student_or_404(db, student_id)
    db.execute(delete(StudentCourse).where(StudentCourse.student_id == student_id))
    if student.card is not None:
        db.delete(student.card)
    db.delete(student)
    commit_or_400(db)


# ==========================================
# ГРУППЫ
# ==========================================
@app.get("/api/groups", response_model=List[GroupWithCount], tags=["Groups"])
def list_groups(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Group, func.count(Student.student_id))
        .outerjoin(Student, Student.group_id == Group.group_id)
        .group_by(Group.group_id)
        .order_by(Group.name)
    ).all()
    return [
        GroupWithCount(**GroupOut.model_validate(group).model_dump(), students_count=count)
        for group, count in rows
    ]


def get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return group


@app.post("/api/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED, tags=["Groups"])
def create_group(data: GroupIn, db: Session = Depends(get_db)):
    group = Group(**data.model_dump())
    db.add(group)
    commit_or_400(db)
    return group


@app.put("/api/groups/{group_id}", response_model=GroupOut, tags=["Groups"])
def update_group(group_id: int, data: GroupIn, db: Session = Depends(get_db)):
    group = get_group_or_404(db, group_id)
    group.name = data.name
    commit_or_400(db)
    return group


@app.delete("/api/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Groups"])
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = get_group_or_404(db, group_id)
    db.delete(group)  # студенты останутся без группы (FK ondelete=SET NULL)
    commit_or_400(db)


# ==========================================
# КУРСЫ
# ==========================================
@app.get("/api/courses", response_model=List[CourseWithCount], tags=["Courses"])
def list_courses(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Course, func.count(StudentCourse.student_id))
        .outerjoin(StudentCourse, StudentCourse.course_id == Course.course_id)
        .group_by(Course.course_id)
        .order_by(Course.name)
    ).all()
    return [
        CourseWithCount(**CourseOut.model_validate(course).model_dump(), students_count=count)
        for course, count in rows
    ]


def get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Курс не найден")
    return course


@app.post("/api/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED, tags=["Courses"])
def create_course(data: CourseIn, db: Session = Depends(get_db)):
    course = Course(**data.model_dump())
    db.add(course)
    commit_or_400(db)
    return course


@app.put("/api/courses/{course_id}", response_model=CourseOut, tags=["Courses"])
def update_course(course_id: int, data: CourseIn, db: Session = Depends(get_db)):
    course = get_course_or_404(db, course_id)
    for field, value in data.model_dump().items():
        setattr(course, field, value)
    commit_or_400(db)
    return course


@app.delete("/api/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Courses"])
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = get_course_or_404(db, course_id)
    db.execute(delete(StudentCourse).where(StudentCourse.course_id == course_id))
    db.delete(course)
    commit_or_400(db)


# ==========================================
# СТУДЕНЧЕСКИЕ БИЛЕТЫ (1:1)
# ==========================================
@app.get("/api/cards", response_model=List[CardOut], tags=["Cards"])
def list_cards(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return db.scalars(select(StudentCard).order_by(StudentCard.card_id).limit(limit).offset(offset)).all()


@app.post("/api/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED, tags=["Cards"])
def create_card(data: CardIn, db: Session = Depends(get_db)):
    student = get_student_or_404(db, data.student_id)
    if student.card is not None:
        raise HTTPException(status_code=400, detail="У студента уже есть билет")
    card = StudentCard(
        card_number=data.card_number,
        student_id=data.student_id,
        **({"issue_date": data.issue_date} if data.issue_date else {}),
    )
    db.add(card)
    commit_or_400(db)
    return card


@app.delete("/api/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Cards"])
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.get(StudentCard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Билет не найден")
    db.delete(card)
    commit_or_400(db)


# ==========================================
# ЗАПИСЬ НА КУРСЫ (N:M)
# ==========================================
@app.post("/api/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED, tags=["Enrollments"])
def enroll(data: EnrollmentIn, db: Session = Depends(get_db)):
    get_student_or_404(db, data.student_id)
    get_course_or_404(db, data.course_id)
    enrollment = StudentCourse(student_id=data.student_id, course_id=data.course_id)
    db.add(enrollment)
    commit_or_400(db)
    return enrollment


@app.delete("/api/enrollments/{student_id}/{course_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Enrollments"])
def unenroll(student_id: int, course_id: int, db: Session = Depends(get_db)):
    enrollment = db.get(StudentCourse, (student_id, course_id))
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Запись на курс не найдена")
    db.delete(enrollment)
    commit_or_400(db)


# ==========================================
# ФРОНТЕНД (собранный SvelteKit) и запуск
# ==========================================
FRONTEND_BUILD = Path(__file__).parent / "frontend" / "build"
if FRONTEND_BUILD.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=8000)