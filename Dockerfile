From python:3.11
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /usr/src/app
RUN pip install --upgrade pip
RUN mkdir -p logs
RUN mkdir -p backend/backend/celerybeat
RUN mkdir -p backend/static
COPY requirements ./requirements
RUN pip install -r requirements/dev.txt
COPY . .