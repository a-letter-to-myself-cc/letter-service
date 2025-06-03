# letters_service/letters/auth_client.py
import requests
from django.conf import settings # settings.py에서 AUTH_SERVICE_URL 등을 가져오기 위함
import logging # 로깅을 위해 추가

# 로거 설정 (선택 사항이지만, 운영 환경에서는 더 체계적인 로깅이 좋습니다)
logger = logging.getLogger(__name__)

# settings.py에 정의될 변수들 (또는 .env 파일을 통해 주입)
# 예: AUTH_SERVICE_BASE_URL = "http://auth-service:8001/auth" (auth-service의 기본 URL)
# 예: AUTH_TOKEN_VERIFY_ENDPOINT = "/internal/verify/" (토큰 검증 API의 실제 경로)
AUTH_SERVICE_BASE_URL = getattr(settings, 'AUTH_SERVICE_BASE_URL', 'http://auth-service:8001/auth')
TOKEN_VERIFY_ENDPOINT = getattr(settings, 'AUTH_TOKEN_VERIFY_ENDPOINT', '/internal/verify/')

class AuthenticationServiceError(Exception):
    """인증 서비스 통신 또는 응답 관련 기본 예외"""
    pass

class TokenVerificationFailed(AuthenticationServiceError):
    """토큰 검증 실패 시 발생하는 예외 (401, 400 등)"""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class AuthServiceConnectionError(AuthenticationServiceError):
    """인증 서비스 연결 실패 시 발생하는 예외"""
    pass

def verify_access_token(access_token: str) -> int: # user_id는 보통 정수형이므로 반환 타입을 int로 명시
    """
    Access Token을 auth-service에 보내 검증하고 user_id를 반환합니다.
    성공 시 user_id (int)를 반환하고, 실패 시 적절한 예외를 발생시킵니다.
    """
    # 개발용 모킹
    if getattr(settings, 'MOCK_USER_SERVICE_AUTH', False):
        logger.info(f"🚧 개발 모드: User Service 인증 호출 모킹됨.")
        # Postman에서 테스트 시 어떤 토큰 값을 보내든 DEV_MOCK_USER_ID를 반환하게 하거나, 
        # 특정 더미 토큰 값에만 반응하도록 한다.
        # 예를 들어, "DUMMY_TOKEN"이라는 값을 Postman에서 보내면 user_id를 반환
        if access_token == "DUMMY_TOKEN_FOR_LETTERS": # Postman에서 이 토큰 값을 사용
            mock_user_id = getattr(settings, 'DEV_MOCK_USER_ID', 999)
            logger.info(f" -> 가짜 User ID ({mock_user_id}) 반환.")
            return mock_user_id
        else:
            logger.warning(f" -> 모킹 모드지만, 유효하지 않은 더미 토큰 값: {access_token}")
            raise TokenVerificationFailed("모킹 모드: 유효하지 않은 더미 토큰입니다.", status_code=401)

    if not access_token:
        logger.warning("🔑 인증 클라이언트: Access Token이 제공되지 않았습니다.")
        raise ValueError("Access Token이 필요합니다.") # 인자 값 오류는 ValueError가 적절
    # 개발용

    verify_url = f"{AUTH_SERVICE_BASE_URL.rstrip('/')}{TOKEN_VERIFY_ENDPOINT.lstrip('/')}"
    payload = {'token': access_token}
    headers = {'Content-Type': 'application/json'}

    logger.info(f"📞 인증 클라이언트: auth-service로 토큰 검증 요청 -> URL: {verify_url}")
    try:
        response = requests.post(verify_url, json=payload, headers=headers, timeout=5) # 타임아웃 설정

        if response.status_code == 200:
            try:
                data = response.json()
                user_id = data.get('user_id')
                if user_id is not None:
                    logger.info(f"✅ 인증 클라이언트: 토큰 검증 성공! User ID: {user_id}")
                    return int(user_id) # user_id를 정수형으로 변환하여 반환
                else:
                    logger.error(f"⚠️ 인증 클라이언트: auth-service 응답에 user_id가 없습니다. 응답: {data}")
                    raise TokenVerificationFailed("auth-service로부터 유효한 user_id를 받지 못했습니다.", status_code=response.status_code)
            except ValueError: # JSON 디코딩 실패
                logger.error(f"📜 인증 클라이언트: auth-service로부터 유효하지 않은 JSON 응답 수신. 상태 코드: {response.status_code}, 응답: {response.text}")
                raise TokenVerificationFailed(f"auth-service로부터 잘못된 형식의 응답을 받았습니다 (상태 코드: {response.status_code}).", status_code=response.status_code)
        
        else: # 200이 아닌 경우 (401, 400, 500 등)
            try:
                error_detail = response.json().get('detail', response.text)
            except ValueError: # 응답이 JSON이 아닐 경우
                error_detail = response.text
            logger.error(f"🚫 인증 클라이언트: 토큰 검증 실패 (상태 코드: {response.status_code}) - {error_detail}")
            raise TokenVerificationFailed(f"토큰 검증 실패: {error_detail}", status_code=response.status_code)

    except requests.exceptions.Timeout:
        logger.error("⏰ 인증 클라이언트: auth-service 토큰 검증 요청 시간 초과.")
        raise AuthServiceConnectionError("auth-service 응답 시간 초과입니다.")
    except requests.exceptions.RequestException as e:
        logger.error(f"💥 인증 클라이언트: auth-service 통신 중 네트워크 오류 발생! {e}")
        raise AuthServiceConnectionError(f"auth-service 통신 중 오류 발생: {e}")
    except Exception as e: # 예상치 못한 기타 예외
        logger.error(f"🤷 인증 클라이언트: 토큰 검증 중 예상치 못한 오류 발생! {e}")
        raise AuthenticationServiceError(f"토큰 검증 중 알 수 없는 오류 발생: {e}")