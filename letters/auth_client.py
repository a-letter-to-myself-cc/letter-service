# auth_client.py

import requests
from django.conf import settings # settings.py에 USER_SERVICE_URL 정의 필요

# USER_SERVICE_URL은 settings.py에 "http://localhost:8001" 등으로 정의되어 있다고 가정합니다.
# (유저 서비스가 실행되는 주소)
# TOKEN_VERIFY_ENDPOINT는 유저 서비스의 실제 토큰 검증 API 경로입니다.
USER_SERVICE_URL = getattr(settings, 'USER_SERVICE_URL', 'http://localhost:8001') # 기본값 설정
TOKEN_VERIFY_ENDPOINT = "/api/auth/internal/token/verify/" # 유저 서비스의 토큰 검증 API 경로 (예시)

def get_user_id_from_token(access_token: str):
    """
    Access Token을 유저 서비스에 보내 검증하고 user_id를 반환합니다.
    성공 시 user_id (int 또는 str), 실패 시 None을 반환합니다.
    """
    if not access_token:
        print("🔑 토큰 클라이언트: Access Token이 제공되지 않았습니다.")
        return None

    verify_url = f"{USER_SERVICE_URL.rstrip('/')}{TOKEN_VERIFY_ENDPOINT}"
    payload = {'token': access_token}
    headers = {'Content-Type': 'application/json'}

    print(f"📞 토큰 클라이언트: 유저 서비스로 토큰 검증 요청 -> URL: {verify_url}")
    try:
        response = requests.post(verify_url, json=payload, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            user_id = data.get('user_id')
            if user_id is not None:
                print(f"✅ 토큰 클라이언트: 토큰 검증 성공! User ID: {user_id}")
                return user_id
            else:
                print(f"⚠️ 토큰 클라이언트: 유저 서비스 응답에 user_id가 없습니다. 응답: {data}")
                return None
        elif response.status_code == 401:
            error_data = response.json()
            error_detail = error_data.get('detail', '알 수 없는 인증 오류')
            print(f"🚫 토큰 클라이언트: 토큰 검증 실패 (401) - {error_detail}")
            return None
        else:
            print(f"❌ 토큰 클라이언트: 토큰 검증 중 서버 오류 (상태 코드: {response.status_code}). 응답: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print("⏰ 토큰 클라이언트: 유저 서비스 응답 시간 초과.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"💥 토큰 클라이언트: 유저 서비스 통신 오류! {e}")
        return None
    except ValueError: # JSONDecodeError
        print(f"📜 토큰 클라이언트: 유저 서비스로부터 유효하지 않은 JSON 응답 수신. 응답: {response.text if 'response' in locals() else '응답 객체 없음'}")
        return None