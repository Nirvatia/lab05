"""Запуск демо-панели одной командой.

  python start.py           продакшен: сборка фронтенда (если нужно) + сервер на http://127.0.0.1:8000
  python start.py --dev     разработка: бэкенд 8000 + SvelteKit с hot-reload на http://127.0.0.1:5173
  python start.py --tunnel  публичный HTTPS-адрес через туннель Cloudflare (доступ из интернета)
  python start.py --reseed  принудительно перегенерировать тестовые данные

MySQL (служба MySQL84), база и тестовые данные проверяются и подготавливаются автоматически.
Остановка: Ctrl+C в терминале, где запущен скрипт.
"""
import argparse
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
BUILD = FRONTEND / "build"
NPM = shutil.which("npm")


def port_open(port, host="127.0.0.1", timeout=1.0):
    with socket.socket() as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def wait_port(port, seconds=90):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(0.5)
    return False


def require_npm():
    if NPM is None:
        sys.exit("[start] npm не найден — установите Node.js: https://nodejs.org")


def our_backend_running():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/stats", timeout=2) as res:
            return res.status == 200
    except Exception:
        return False


def check_backend_port():
    if port_open(8000) and not our_backend_running():
        sys.exit("[start] Порт 8000 занят другим процессом. Освободите его или смените порт в api.py.")


def ensure_mysql():
    if port_open(3306):
        return
    print("[start] MySQL не запущен — поднимаю службу MySQL84…")
    result = subprocess.run(["net", "start", "MySQL84"], capture_output=True, text=True)
    if result.returncode != 0:
        print("[start] Для запуска службы нужны права администратора — запрос UAC…")
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Start-Process net -ArgumentList 'start','MySQL84' -Verb RunAs -Wait"],
            check=False,
        )
    if not wait_port(3306, 30):
        sys.exit("[start] Не удалось запустить MySQL. Запустите службу MySQL84 вручную.")


def ensure_database(reseed=False):
    import pymysql

    conn = pymysql.connect(host="127.0.0.1", user="root", password="")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS students_orm "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()

    from sqlalchemy import func, select

    from db import engine
    from models import Student, Students

    Students.metadata.create_all(engine)
    with engine.connect() as conn:
        count = conn.scalar(select(func.count()).select_from(Student))
    if count == 0 or reseed:
        from seed import seed

        seed()
    else:
        print(f"[start] В базе уже есть данные ({count} студентов) — оставляю как есть.")


def ensure_node_modules():
    require_npm()
    if not (FRONTEND / "node_modules").is_dir():
        print("[start] Устанавливаю npm-зависимости…")
        subprocess.run([NPM, "install"], cwd=FRONTEND, check=True)


def frontend_needs_build():
    index = BUILD / "index.html"
    if not index.exists():
        return True
    built = index.stat().st_mtime
    sources = list((FRONTEND / "src").rglob("*")) + [
        FRONTEND / "vite.config.js",
        FRONTEND / "package.json",
    ]
    return any(p.is_file() and p.stat().st_mtime > built for p in sources)


def build_frontend():
    ensure_node_modules()
    print("[start] Собираю фронтенд…")
    subprocess.run([NPM, "run", "build"], cwd=FRONTEND, check=True)


def open_browser_when_ready(url, port):
    def worker():
        if wait_port(port):
            webbrowser.open(url)

    threading.Thread(target=worker, daemon=True).start()


def kill_tree(proc):
    if proc.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


def run_prod(reseed):
    ensure_mysql()
    ensure_database(reseed)
    check_backend_port()
    if frontend_needs_build():
        build_frontend()
    else:
        print("[start] Фронтенд уже собран и актуален.")

    if our_backend_running():
        print("[start] Сервер уже работает: http://127.0.0.1:8000")
        webbrowser.open("http://127.0.0.1:8000")
        return

    print("[start] Сервер: http://127.0.0.1:8000  (остановка — Ctrl+C)")
    open_browser_when_ready("http://127.0.0.1:8000", 8000)
    try:
        subprocess.run([sys.executable, "api.py"], cwd=ROOT)
    except KeyboardInterrupt:
        pass


def run_dev(reseed):
    ensure_mysql()
    ensure_database(reseed)
    check_backend_port()
    ensure_node_modules()

    backend = None
    if our_backend_running():
        print("[start] Бэкенд уже работает на 8000 — использую его.")
    else:
        backend = subprocess.Popen([sys.executable, "api.py"], cwd=ROOT)

    print("[start] Запускаю SvelteKit dev-сервер… (остановка — Ctrl+C)")
    frontend = subprocess.Popen(
        [NPM, "run", "dev", "--", "--host", "127.0.0.1"],
        cwd=FRONTEND,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Vite может занять другой порт, если 5173 занят, — читаем фактический адрес из вывода
    actual_port = None

    def pump_output():
        nonlocal actual_port
        for line in frontend.stdout:
            print(line, end="")
            match = re.search(r"http://127\.0\.0\.1:(\d+)", line)
            if match and actual_port is None:
                actual_port = int(match.group(1))

    threading.Thread(target=pump_output, daemon=True).start()

    deadline = time.time() + 90
    while actual_port is None and time.time() < deadline and frontend.poll() is None:
        time.sleep(0.3)
    if actual_port is None:
        kill_tree(frontend)
        if backend is not None:
            kill_tree(backend)
        sys.exit("[start] Dev-сервер не запустился (см. вывод выше).")

    url = f"http://127.0.0.1:{actual_port}"
    print(f"[start] Фронтенд с hot-reload: {url}")
    open_browser_when_ready(url, actual_port)
    try:
        while True:
            if frontend.poll() is not None:
                break
            if backend is not None and backend.poll() is not None:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        kill_tree(frontend)
        if backend is not None:
            kill_tree(backend)


def find_cloudflared():
    path = shutil.which("cloudflared")
    if path:
        return path
    for candidate in (
        Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe"),
        Path(r"C:\Program Files\cloudflared\cloudflared.exe"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def run_tunnel(reseed):
    ensure_mysql()
    ensure_database(reseed)
    check_backend_port()
    if frontend_needs_build():
        build_frontend()
    else:
        print("[start] Фронтенд уже собран и актуален.")

    cloudflared = find_cloudflared()
    if cloudflared is None:
        sys.exit("[start] cloudflared не найден. Установите: winget install Cloudflare.cloudflared")

    backend = None
    if our_backend_running():
        print("[start] Бэкенд уже работает на 8000 — использую его.")
    else:
        print("[start] Запускаю сервер на 127.0.0.1:8000…")
        backend = subprocess.Popen([sys.executable, "api.py"], cwd=ROOT)
        if not wait_port(8000, 30):
            kill_tree(backend)
            sys.exit("[start] Сервер не запустился.")

    print("[start] Поднимаю туннель Cloudflare…")
    tunnel = subprocess.Popen(
        [cloudflared, "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    public_url = None

    def pump_output():
        nonlocal public_url
        for line in tunnel.stdout:
            print(line, end="")
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match and public_url is None:
                public_url = match.group(0)

    threading.Thread(target=pump_output, daemon=True).start()

    deadline = time.time() + 60
    while public_url is None and time.time() < deadline and tunnel.poll() is None:
        time.sleep(0.3)
    if public_url is None:
        kill_tree(tunnel)
        if backend is not None:
            kill_tree(backend)
        sys.exit("[start] Не удалось получить адрес туннеля (см. вывод выше).")

    print()
    print("=" * 64)
    print(f"  Публичный адрес: {public_url}")
    print("  Откройте его с любого устройства в интернете.")
    print("  Остановка — Ctrl+C (погасит туннель и сервер).")
    print("=" * 64)
    webbrowser.open(public_url)
    try:
        while True:
            if tunnel.poll() is not None:
                break
            if backend is not None and backend.poll() is not None:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        kill_tree(tunnel)
        if backend is not None:
            kill_tree(backend)


def main():
    parser = argparse.ArgumentParser(description="Запуск демо-панели Students ORM")
    parser.add_argument("--dev", action="store_true",
                        help="режим разработки с hot-reload фронтенда (порт 5173)")
    parser.add_argument("--tunnel", action="store_true",
                        help="публичный HTTPS-адрес через туннель Cloudflare")
    parser.add_argument("--reseed", action="store_true",
                        help="перегенерировать тестовые данные")
    args = parser.parse_args()

    if args.dev:
        run_dev(args.reseed)
    elif args.tunnel:
        run_tunnel(args.reseed)
    else:
        run_prod(args.reseed)


if __name__ == "__main__":
    main()