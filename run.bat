@echo off

Rem Go to script location
cd /d %~dp0
Rem Activate venv
call venv/Scripts/activate.bat

Rem Run tests and Start server
start /min cmd /K "cd backend & python manage.py runserver"
Rem Start celery worker
start /min cmd /K "cd backend & celery -A backend worker -l info -P solo"
Rem Start celery beat
start /min cmd /K "cd backend & celery -A backend beat -s backend/celerybeat/celerybeat-schedule"

echo Note: Redis and Postgres need to be started separately (WSL recommended for Redis)
timeout /t 5
echo. & echo Upcoming events:
curl http://127.0.0.1:8000/event/

echo. & echo.
echo Request examples:
echo curl http://127.0.0.1:8000/event/
echo curl http://127.0.0.1:8000/event/?query=EQUAL(type,"uni")
echo curl -d "title=example&date=2025-01-01" -X POST http://127.0.0.1:8000/event/
echo.

cmd /k
