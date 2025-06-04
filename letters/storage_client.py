# letters/storage_service_client.py
import requests
from django.conf import settings

# 기본 스토리지 서비스 URL 가져오기
STORAGE_API_BASE_URL = settings.LETTER_STORAGE_SERVICE_BASE_URL.rstrip('/')

def upload_image_to_storage(file_to_upload):
    """
    이미지 파일을 스토리지 서비스에 업로드하고 blob 이름을 반환합니다.
    성공 시 blob_name, 실패 시 None을 반환합니다.
    """
    gcs_blob_name = None
    if not file_to_upload:
        print("📤 스토리지 클라이언트: 업로드할 파일이 없습니다.")
        return None

    upload_api_path = "/api/images/"  # 스토리지 서비스의 실제 업로드 API 경로
    full_upload_api_url = f"{STORAGE_API_BASE_URL}{upload_api_path}"
    
    print(f"📞 스토리지 클라이언트: 이미지 업로드 API 호출 시도... URL: {full_upload_api_url}")
    try:
        files_payload = {'file': (file_to_upload.name, file_to_upload, file_to_upload.content_type)}
        
        response = requests.post(full_upload_api_url, files=files_payload)
        response.raise_for_status()  # 오류 발생 시 HTTPError 예외 발생
        
        upload_response_data = response.json()

        if upload_response_data.get('blob_name'):
            gcs_blob_name = upload_response_data.get('blob_name')
            print(f"✅ 스토리지 클라이언트: 이미지 업로드 성공! Blob Name: {gcs_blob_name}")
        else:
            error_message = upload_response_data.get('message', '알 수 없는 응답 형식')
            print(f"❌ 스토리지 클라이언트: 이미지 업로드 API 응답 오류 - {error_message}")
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ 스토리지 클라이언트: 이미지 업로드 API HTTP 오류! 상태 코드: {e.response.status_code}, 응답: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 스토리지 클라이언트: 이미지 업로드 API 요청 오류! {e}")
    except ValueError: # JSON 디코딩 오류
        print(f"❌ 스토리지 클라이언트: 이미지 업로드 API 응답 JSON 디코딩 오류! 응답: {response.text if 'response' in locals() else '응답 객체 없음'}")
    except Exception as e:
        print(f"❌ 스토리지 클라이언트: 이미지 업로드 중 예상치 못한 오류 발생! {e}")
        
    return gcs_blob_name


def get_signed_url_from_storage(blob_name):
    """
    스토리지 서비스로부터 이미지 blob 이름에 대한 서명된 URL을 가져옵니다.
    성공 시 signed_url, 실패 시 None을 반환합니다.
    """
    signed_url = None
    if not blob_name:
        print("🔗 스토리지 클라이언트: 서명된 URL을 생성할 blob 이름이 없습니다.")
        return None

    get_url_api_path = f"/api/images/{blob_name}/"  # 경로 마지막 / 유의
    full_get_url_api_url = f"{STORAGE_API_BASE_URL}{get_url_api_path}"

    print(f"📞 스토리지 클라이언트: 서명된 URL 생성 API 호출 시도... URL: {full_get_url_api_url}")
    try:
        response = requests.get(full_get_url_api_url)
        response.raise_for_status()
        
        url_response_data = response.json()

        if url_response_data.get('signed_url'):
            signed_url = url_response_data.get('signed_url')
            print(f"✅ 스토리지 클라이언트: 서명된 URL 생성 성공! URL: {signed_url} (Blob: {blob_name})")
        else:
            error_message = url_response_data.get('message', '알 수 없는 응답 형식')
            print(f"❌ 스토리지 클라이언트: 서명된 URL 생성 API 응답 오류 - {error_message}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ 스토리지 클라이언트: 서명된 URL 생성 API HTTP 오류! 상태 코드: {e.response.status_code}, 응답: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 스토리지 클라이언트: 서명된 URL 생성 API 요청 오류! {e}")
    except ValueError: # JSON 디코딩 오류
        print(f"❌ 스토리지 클라이언트: 서명된 URL 생성 API 응답 JSON 디코딩 오류! 응답: {response.text if 'response' in locals() else '응답 객체 없음'}")
    except Exception as e:
        print(f"❌ 스토리지 클라이언트: 서명된 URL 생성 중 예상치 못한 오류 발생! {e}")
        
    return signed_url


def delete_image_from_storage(blob_name):
    """
    스토리지 서비스에서 이미지를 삭제합니다.
    성공 시 True, 실패 시 False를 반환합니다.
    """
    if not blob_name:
        print("🗑️ 스토리지 클라이언트: 삭제할 이미지의 blob 이름이 없습니다.")
        return False

    delete_api_path = f"/api/images/{blob_name}/"
    full_delete_api_url = f"{STORAGE_API_BASE_URL}{delete_api_path}"

    print(f"📞 스토리지 클라이언트: 이미지 삭제 API 호출 시도... URL: DELETE {full_delete_api_url}")
    try:
        response = requests.delete(full_delete_api_url)

        if response.status_code == 204:  # 성공 (No Content)
            print(f"✅ 스토리지 클라이언트: 이미지 '{blob_name}' 삭제 성공 (204 No Content).")
            return True
        elif response.ok:  # 다른 2xx 성공 코드
            try:
                delete_response_data = response.json()
                print(f"✅ 스토리지 클라이언트: 이미지 '{blob_name}' 삭제 응답 (상태코드 {response.status_code}): {delete_response_data}")
            except ValueError:
                print(f"✅ 스토리지 클라이언트: 이미지 '{blob_name}' 삭제 성공 (상태코드: {response.status_code}), 응답 본문 JSON 아님: {response.text}")
            return True
        else:
            response.raise_for_status() # HTTP 오류 발생
            return False # raise_for_status가 예외를 발생시키므로 이 줄은 실행되지 않을 수 있음

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"ℹ️ 스토리지 클라이언트: 삭제할 이미지 '{blob_name}'를 GCS 또는 스토리지 서비스에서 찾을 수 없습니다 (HTTP 404).")
        else:
            print(f"❌ 스토리지 클라이언트: 이미지 삭제 API HTTP 오류! 상태 코드: {e.response.status_code}, 응답: {e.response.text if e.response else '응답 텍스트 없음'}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 스토리지 클라이언트: 이미지 삭제 API 요청 오류! {e}")
        return False
    except Exception as e:
        print(f"❌ 스토리지 클라이언트: 이미지 삭제 API 호출 중 예상치 못한 오류 발생! {e}")
        return False