# 1. 베이스 이미지
FROM python:3.13-slim

# 2. 환경 변수
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 작업 디렉토리
WORKDIR /app

# 4. (필요시) 시스템 의존성 설치
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# 5. Python 의존성 설치 (캐시 활용을 위해 requirements.txt 먼저 복사)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. 프로젝트 전체 파일 복사
COPY . /app/

# 7. (필요시) 정적 파일 수집
# RUN python manage.py collectstatic --noinput

# 8. 포트 노출
EXPOSE 8000

# 9. 실행 명령어 (개발용 또는 프로덕션용 WSGI 서버)
# Django 프로젝트 폴더 이름이 'my_project_config'라고 가정 (wsgi.py가 있는 곳)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# 또는 프로덕션용 Gunicorn:
# CMD ["gunicorn", "my_project_config.wsgi:application", "--bind", "0.0.0.0:8000"]