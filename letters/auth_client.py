# letters_service/letters/auth_client.py
import requests
from django.conf import settings

AUTH_SERVICE_URL = getattr(settings, 'AUTH_SERVICE_URL', 'http://auth-service:8001/auth')
TOKEN_VERIFY_ENDPOINT = getattr(settings, 'AUTH_TOKEN_VERIFY_ENDPOINT', '/internal/verify/')


def verify_access_token(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{AUTH_SERVICE_URL}/internal/verify/", headers=headers)
        if response.status_code == 200:
            return response.json()['user_id']
        else:
            try:
                return_detail = response.json().get('detail', response.text)
            except Exception:
                return_detail = response.text
            raise Exception(f"Token verificaion failed: {return_detail}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Auth service connection failed: {str(e)}")

