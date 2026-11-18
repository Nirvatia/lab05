from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    create_engine, Integer, String, Numeric,
    Text, ForeignKey, DateTime, Date, CheckConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Students(DeclarativeBase):
    pass


class StudentCourse(Students):
    __tablename__ = "students_courses"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id"), primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id"), primary_key=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())


class Course(Students):
    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    students: Mapped[List["Student"]] = relationship(
        secondary="students_courses", back_populates="courses"
    )


class Group(Students):
    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    students: Mapped[List["Student"]] = relationship("Student", back_populates="group")


class Student(Students):
    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("groups.group_id", ondelete="SET NULL"), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("age >= 16", name="check_student_age"),
        CheckConstraint("email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", name="check_student_email"),
    )

    group: Mapped[Optional[Group]] = relationship("Group", back_populates="students")
    card: Mapped[Optional["StudentCard"]] = relationship("StudentCard", back_populates="student", uselist=False)
    courses: Mapped[List[Course]] = relationship(secondary="students_courses", back_populates="students")


class StudentCard(Students):
    __tablename__ = "student_cards"

    card_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, default=func.curdate())
    student_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), unique=True, nullable=True
    )

    student: Mapped[Optional[Student]] = relationship("Student", back_populates="card")


if __name__ == "__main__":
    DATABASE_URL = "mysql+pymysql://root:@127.0.0.1:3306/students_orm"

    engine = create_engine(DATABASE_URL, echo=True)

    print("Создаем таблицы в базе данных")
    Students.metadata.create_all(engine)
    print("Все таблицы и связи успешно созданы")
