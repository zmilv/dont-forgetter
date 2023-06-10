From python:3.11
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /usr/src/app
EXPOSE 8000
COPY . .
RUN pip install --upgrade pip && \
    pip install -r requirements/dev.txt && \
    mkdir -p logs && \
    mkdir -p backend/backend/celerybeat
