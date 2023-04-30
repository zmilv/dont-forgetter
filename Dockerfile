From python:3.11
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /usr/src/app
RUN mkdir -p logs
RUN mkdir -p backend/backend/celerybeat
COPY requirements.txt ./
RUN pip install -r requirements.txt
