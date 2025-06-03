#!/bin/sh

# 데이터베이스가 준비될 때까지 기다리는 로직 (선택 사항이지만 권장)
# 예: dockerize -wait tcp://db:5432 -timeout 60s

echo "데이터베이스 마이그레이션 적용 중..."
python manage.py migrate --noinput

echo "Django 애플리케이션 서버 시작 중..."
exec python manage.py runserver 0.0.0.0:8000 # 개발 서버
# exec gunicorn your_project_name.wsgi:application --bind 0.0.0.0:8000 # 프로덕션 서버