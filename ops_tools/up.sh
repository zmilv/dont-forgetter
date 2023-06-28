#!/bin/bash

# Usage: . ops_tools/up.sh

source env_vars/.env.prod

export DJANGO_IMAGE=$DJANGO_IMAGE
export DJANGO_MIGRATIONS_IMAGE=$DJANGO_MIGRATIONS_IMAGE
export CELERY_IMAGE=$CELERY_IMAGE
export CELERY_BEAT_IMAGE=$CELERY_BEAT_IMAGE
export NGINX_IMAGE=$NGINX_IMAGE

docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
