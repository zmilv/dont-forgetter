From python:3.11
ARG env
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /usr/src/app
EXPOSE 8000
COPY . .
RUN pip install --upgrade pip && \
    if [ "${env}" = "prod" ] ; then pip install -r requirements/prod.txt ; else pip install -r requirements/dev.txt ; fi
