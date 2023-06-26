#!/bin/bash

docker-compose exec django python manage.py makemigrations --noinput
docker-compose exec django python manage.py migrate
