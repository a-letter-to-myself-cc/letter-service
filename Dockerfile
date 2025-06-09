# 1. 베이스 이미지
FROM python:3.13-slim

# 2. Python 관련 기본 환경 변수
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 종속성 설치 (이 부분을 먼저 실행하여 레이어 캐시 활용)
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ✅ curl 설치 (이 부분을 추가합니다)
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/* # 캐시 정리

# 5. entrypoint.sh 복사 및 실행 권한 부여
#   - 스크립트를 코드와 함께 /app 디렉토리에 두는 것이 일반적입니다.
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 6. 나머지 소스 코드 복사
COPY . /app/

# 7. 컨테이너 실행 명령 (경로 변경에 주의)
ENTRYPOINT ["/app/entrypoint.sh"]