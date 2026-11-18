import mysql.connector
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

# Инициализируем FastAPI с заголовками для Swagger
app = FastAPI(
    title="Students СRUD API",
    description="REST API для управления студентами с автоматической документацией Swagger",
    version="1.0.0"
)

# Настройки вашей базы данных
DB_CONFIG = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'students',
}


def get_db_connection():
    """Функция для быстрого подключения к БД"""
    return mysql.connector.connect(**DB_CONFIG)


# ==========================================
# PYDANTIC МОДЕЛИ (Валидация входящих/исходящих данных)
# ==========================================
class StudentBase(BaseModel):
    name: str = Field(..., example="Иванов Иван Иванович")
    group_id: Optional[int] = Field(None, example=1)
    email: str = Field(..., example="ivanov@example.com")  # Для строгой проверки почты можно использовать EmailStr
    age: int = Field(..., ge=16, example=20)  # ge=16 валидирует CHECK constraint из вашей БД


class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    student_id: int

    class Config:
        from_attributes = True


# ==========================================
# CRUD ОПЕРАЦИИ (Эндпоинты API)
# ==========================================

@app.post("/students/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, tags=["Students"])
def create_student(student: StudentCreate):
    """**CREATE**: Добавить нового студента в базу данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "INSERT INTO `students` (name, group_id, email, age) VALUES (%s, %s, %s, %s)"
        values = (student.name, student.group_id, student.email, student.age)

        cursor.execute(query, values)
        conn.commit()

        # Получаем ID созданной записи
        new_id = cursor.lastrowid
        return {**student.model_dump(), "student_id": new_id}

    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=f"Ошибка БД: {err}")
    finally:
        cursor.close()
        conn.close()


@app.get("/students/", response_model=List[StudentResponse], tags=["Students"])
def read_students(limit: int = 100, offset: int = 0):
    """**READ**: Получить список всех студентов (с пагинацией)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # dictionary=True возвращает строки как dict

        query = "SELECT student_id, name, group_id, email, age FROM `students` LIMIT %s OFFSET %s"
        cursor.execute(query, (limit, offset))

        return cursor.fetchall()
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Ошибка БД: {err}")
    finally:
        cursor.close()
        conn.close()


@app.get("/students/{student_id}", response_model=StudentResponse, tags=["Students"])
def read_student(student_id: int):
    """**READ**: Получить информацию о конкретном студенте по ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT student_id, name, group_id, email, age FROM `students` WHERE student_id = %s"
        cursor.execute(query, (student_id,))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Студент не найден")
        return result
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Ошибка БД: {err}")
    finally:
        cursor.close()
        conn.close()


@app.put("/students/{student_id}", response_model=StudentResponse, tags=["Students"])
def update_student(student_id: int, student: StudentCreate):
    """**UPDATE**: Обновить данные студента по ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем существование
        cursor.execute("SELECT student_id FROM `students` WHERE student_id = %s", (student_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Студент не найден")

        query = "UPDATE `students` SET name = %s, group_id = %s, email = %s, age = %s WHERE student_id = %s"
        values = (student.name, student.group_id, student.email, student.age, student.id)

        cursor.execute(query, values)
        conn.commit()

        return {**student.model_dump(), "student_id": student_id}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=f"Ошибка БД: {err}")
    finally:
        cursor.close()
        conn.close()


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
def delete_student(student_id: int):
    """**DELETE**: Удалить студента по ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем существование
        cursor.execute("SELECT student_id FROM `students` WHERE student_id = %s", (student_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Студент не найден")

        cursor.execute("DELETE FROM `students` WHERE student_id = %s", (student_id,))
        conn.commit()
        return None
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=f"Ошибка БД: {err}")
    finally:
        cursor.close()
        conn.close()


# Запуск локального сервера (удобно для запуска прямо из PyCharm)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
