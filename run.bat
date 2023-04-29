@echo off

cd /d %~dp0 Rem Go to script location
call venv/Scripts/activate.bat Rem Activate venv

start /min cmd /C "cd backend & python manage.py test core.tests" Rem Run tests

start /min cmd /C "cd backend & python manage.py runserver" Rem Start server
start /min cmd /C "cd backend & celery -A backend worker -l info -P solo" Rem Start celery worker
start /min cmd /C "cd backend & celery -A backend beat -s backend/celerybeat/celerybeat-schedule" Rem Start celery beat

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
