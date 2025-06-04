FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]




# # ARG 방식식

# # 1. 베이스 이미지 (Python 버전은 실제 프로젝트에 맞게 조정)
# ARG PYTHON_VERSION=3.13
# FROM python:${PYTHON_VERSION}-slim

# # 2. 빌드 시점에 전달받을 ARG 변수들 선언
# # settings.py에서 os.getenv()로 참조하는 모든 변수를 ARG로 선언합니다.
# # 민감 정보(비밀번호, SECRET_KEY 등)는 ARG에 기본값을 설정하지 않습니다.
# ARG SECRET_KEY
# ARG DEBUG=False # 기본값은 False (프로덕션 환경 고려)
# ARG ALLOWED_HOSTS="*" # 기본값은 모든 호스트 허용 (프로덕션에서는 구체적으로 명시)

# ARG DB_NAME
# ARG DB_USER
# ARG DB_PASSWORD
# ARG DB_HOST=letters-db
# ARG DB_PORT=5432

# ARG RABBITMQ_HOST=rabbitmq
# ARG RABBITMQ_PORT=5672
# ARG RABBITMQ_VHOST=/
# ARG RABBITMQ_USER
# ARG RABBITMQ_PASSWORD

# ARG AUTH_SERVICE_URL
# ARG AUTH_TOKEN_VERIFY_ENDPOINT

# ARG DJANGO_SETTINGS_MODULE=letter_project.settings
# ARG APP_PORT=8000

# # 3. Python 관련 기본 환경 변수
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # 4. ARG로 받은 값들을 런타임 환경 변수(ENV)로 설정
# ENV SECRET_KEY=${SECRET_KEY}
# ENV DEBUG=${DEBUG}
# ENV ALLOWED_HOSTS=${ALLOWED_HOSTS}

# ENV DB_NAME=${DB_NAME}
# ENV DB_USER=${DB_USER}
# ENV DB_PASSWORD=${DB_PASSWORD}
# ENV DB_HOST=${DB_HOST}
# ENV DB_PORT=${DB_PORT}

# ENV RABBITMQ_HOST=${RABBITMQ_HOST}
# ENV RABBITMQ_PORT=${RABBITMQ_PORT}
# ENV RABBITMQ_VHOST=${RABBITMQ_VHOST}
# ENV RABBITMQ_USER=${RABBITMQ_USER}
# ENV RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD}

# ENV AUTH_SERVICE_URL=${AUTH_SERVICE_URL}
# ENV AUTH_TOKEN_VERIFY_ENDPOINT=${AUTH_TOKEN_VERIFY_ENDPOINT}

# ENV GOOGLE_APPLICATION_CREDENTIALS_JSON=${GOOGLE_APPLICATION_CREDENTIALS_JSON}
# ENV GCS_BUCKET_NAME=${GCS_BUCKET_NAME}
# ENV GCP_PROJECT_ID=${GCP_PROJECT_ID}

# ENV DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}
# ENV APP_PORT=${APP_PORT}

# # 5. 작업 디렉토리 설정
# WORKDIR /app

# # 6. 종속성 파일 복사 및 설치
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# # 7. entrypoint.sh 복사 및 실행 권한 부여 (만약 사용한다면)
# COPY entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh
# RUN apt-get update && apt-get install -y netcat-openbsd # DB 대기 등에 netcat 사용 시 (선택 사항)

# # 8. 나머지 애플리케이션 코드 복사
# COPY . /app/

# # 9. 애플리케이션 포트 노출 (ENV 변수 사용)
# EXPOSE ${APP_PORT}

# # 10. 컨테이너 실행 명령
# ENTRYPOINT ["/entrypoint.sh"]
# # entrypoint.sh가 CMD 인자를 받는다면: CMD ["python", "manage.py", "runserver", "0.0.0.0:${APP_PORT}"]
# # entrypoint.sh를 사용하지 않는다면 바로 서버 실행:
# # CMD ["python", "manage.py", "runserver", "0.0.0.0:${APP_PORT}"]

# # 만약 entrypoint.sh를 사용하고, 그 스크립트가 APP_PORT를 참조하여 서버를 실행한다면
# # ENTRYPOINT ["/entrypoint.sh"]
# # CMD [] # 또는 CMD ["gunicorn", "letter_project.wsgi:application", "--bind", "0.0.0.0:${APP_PORT}"] 등 프로덕션 서버 명령