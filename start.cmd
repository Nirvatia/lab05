@echo off
rem Запуск демо двойным кликом. Режим разработки: start.cmd --dev
cd /d "%~dp0"
python start.py %*
pause