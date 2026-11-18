"""Смоук-тест API демо-панели. Запускать при работающем сервере: python api.py, затем python test_api.py."""
import json
import unittest
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        with e:
            raw = e.read()
        return e.code, json.loads(raw) if raw else None


def cleanup_leftovers():
    """Удаляет тестовые сущности, оставшиеся от прерванного прогона."""
    _, page = call("GET", "/api/students?search=smoke_test@example.com")
    for s in page["items"]:
        call("DELETE", f"/api/students/{s['student_id']}")
    _, courses = call("GET", "/api/courses")
    for c in courses:
        if c["name"] == "Тест-курс":
            call("DELETE", f"/api/courses/{c['course_id']}")
    _, groups = call("GET", "/api/groups")
    for g in groups:
        if g["name"] == "ТЕСТ-99":
            call("DELETE", f"/api/groups/{g['group_id']}")


class ApiSmokeTest(unittest.TestCase):
    def test_full_cycle(self):
        cleanup_leftovers()

        # статистика и фронтенд
        status, stats = call("GET", "/api/stats")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(stats["students"], 1000)

        req = urllib.request.Request(BASE + "/")
        with urllib.request.urlopen(req, timeout=10) as res:
            self.assertEqual(res.status, 200)
            self.assertIn("text/html", res.headers["Content-Type"])

        # группа: создание, дубликат, список
        status, group = call("POST", "/api/groups", {"name": "ТЕСТ-99"})
        self.assertEqual(status, 201)
        gid = group["group_id"]
        status, _ = call("POST", "/api/groups", {"name": "ТЕСТ-99"})
        self.assertEqual(status, 400)
        status, groups = call("GET", "/api/groups")
        self.assertEqual(status, 200)
        self.assertTrue(any(g["group_id"] == gid for g in groups))

        # студент: создание, чтение, обновление, валидация
        payload = {"name": "Тестов Тест Тестович", "email": "smoke_test@example.com",
                   "age": 20, "group_id": gid}
        status, student = call("POST", "/api/students", payload)
        self.assertEqual(status, 201)
        sid = student["student_id"]
        self.assertEqual(student["group"]["name"], "ТЕСТ-99")

        status, got = call("GET", f"/api/students/{sid}")
        self.assertEqual(status, 200)
        self.assertEqual(got["email"], "smoke_test@example.com")

        status, updated = call("PUT", f"/api/students/{sid}", {**payload, "age": 21})
        self.assertEqual(status, 200)
        self.assertEqual(updated["age"], 21)

        status, _ = call("POST", "/api/students", {**payload, "age": 15})
        self.assertEqual(status, 422)  # Pydantic: ge=16

        # билет (1:1): выдача, повторная выдача запрещена
        status, card = call("POST", "/api/cards", {"card_number": "ST-TEST-001", "student_id": sid})
        self.assertEqual(status, 201)
        status, _ = call("POST", "/api/cards", {"card_number": "ST-TEST-002", "student_id": sid})
        self.assertEqual(status, 400)
        status, got = call("GET", f"/api/students/{sid}")
        self.assertEqual(got["card"]["card_number"], "ST-TEST-001")

        # курс и запись на курс (N:M)
        status, course = call("POST", "/api/courses", {"name": "Тест-курс", "price": 99.99,
                                                       "description": "временный курс"})
        self.assertEqual(status, 201)
        cid = course["course_id"]
        status, _ = call("POST", "/api/enrollments", {"student_id": sid, "course_id": cid})
        self.assertEqual(status, 201)
        status, _ = call("POST", "/api/enrollments", {"student_id": sid, "course_id": cid})
        self.assertEqual(status, 400)  # составной PK
        status, got = call("GET", f"/api/students/{sid}")
        self.assertIn(cid, [c["course_id"] for c in got["courses"]])

        # поиск
        status, page = call("GET", "/api/students?search=smoke_test@example.com")
        self.assertEqual(status, 200)
        self.assertEqual(page["total"], 1)

        # удаление в обратном порядке
        status, _ = call("DELETE", f"/api/enrollments/{sid}/{cid}")
        self.assertEqual(status, 204)
        status, _ = call("DELETE", f"/api/cards/{card['card_id']}")
        self.assertEqual(status, 204)
        status, _ = call("DELETE", f"/api/students/{sid}")
        self.assertEqual(status, 204)
        status, _ = call("GET", f"/api/students/{sid}")
        self.assertEqual(status, 404)
        status, _ = call("DELETE", f"/api/courses/{cid}")
        self.assertEqual(status, 204)
        status, _ = call("DELETE", f"/api/groups/{gid}")
        self.assertEqual(status, 204)


if __name__ == "__main__":
    unittest.main(verbosity=2)