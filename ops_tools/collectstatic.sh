#!/bin/bash

docker-compose exec django python manage.py collectstatic --noinput
