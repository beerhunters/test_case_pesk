FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001

# Установите Redis клиент (если его нет в базовом образе)
RUN pip install redis

EXPOSE 5001

CMD ["flask", "run"]