@echo off

cd /d %~dp0
call venv/Scripts/activate.bat

start /min cmd /C "cd backend & python manage.py runserver"
start /min cmd /K "cd backend & celery -A backend worker -l info -P solo"
start /min cmd /K "cd backend & celery -A backend beat"

timeout /t 3
echo. & echo Upcoming events:
curl http://127.0.0.1:8000/event/

echo. & echo.
echo Request examples:
echo curl http://127.0.0.1:8000/event/
echo curl http://127.0.0.1:8000/event/?query=EQUAL(type,"uni")
echo curl -d "title=example&date=2025-01-01" -X POST http://127.0.0.1:8000/event/
echo.

cmd /k
