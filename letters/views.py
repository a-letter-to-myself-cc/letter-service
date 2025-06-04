from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from .models import Letters
from .forms import LetterForm
from django.utils.timezone import now  # 현재 날짜 가져오기
# from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt # 테스트 환경에서 필요한 인증
from django.views.decorators.http import require_http_methods
from datetime import datetime
from django.conf import settings
# 스토리지, 토큰, 이모션 파일들 임포트
from .storage_client import upload_image_to_storage, get_signed_url_from_storage, delete_image_from_storage
from .auth_client import verify_access_token, TokenVerificationFailed, AuthServiceConnectionError
from .message_producers import publish_emotion_analysis_request
import logging

logger = logging.getLogger(__name__)

def some_protected_view(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Authorization 헤더가 Bearer 토큰 형식으로 필요합니다.'}, status=401)
    
    token = auth_header.split(' ')[1]
    
    try:
        user_id = verify_access_token(token)
        return JsonResponse({'message': f'성공! 사용자 ID: {user_id}'}) # user id 반환
    
    except ValueError as ve: # 토큰 미제공 등 입력값 오류
        return JsonResponse({'error': str(ve)}, status=400)
    except TokenVerificationFailed as tvf: # 토큰 검증 실패 (auth-service가 거부)
        return JsonResponse({'error': str(tvf), 'auth_status_code': tvf.status_code}, status=401) # 또는 tvf.status_code 직접 사용
    except AuthServiceConnectionError as ace: # auth-service 연결 불가
        return JsonResponse({'error': f'인증 서비스에 연결할 수 없습니다: {str(ace)}'}, status=503) # Service Unavailable
    except Exception as e: # 기타 예상치 못한 오류
        return JsonResponse({'error': f'알 수 없는 오류 발생: {str(e)}'}, status=500)

def home(request):
    # 필요하다면 인증 로직 추가 가능.
    return render(request, 'myapp/index.html')

# 1️⃣ 편지 작성 뷰
# @login_required(login_url='/auth/login/')  # 👈 직접 로그인 URL 지정 (auth 마이크로서비스)
def write_letter(request):
    # 1. 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("🔑 편지 작성: Authorization 헤더 누락 또는 Bearer 타입 아님.")
        return JsonResponse({'error': 'Authorization 헤더가 Bearer 토큰 형식으로 필요합니다.'}, status=401)

    token = auth_header.split(' ')[1]
    user_id_from_token = None

    try:
        user_id_from_token = verify_access_token(token)
        logger.info(f"👤 편지 작성: 인증된 사용자 ID {user_id_from_token} 확인.")
    except TokenVerificationFailed as tvf:
        return JsonResponse({'error': str(tvf)}, status=401)
    except AuthServiceConnectionError as ace:
        return JsonResponse({'error': f'인증 서비스에 연결할 수 없습니다: {str(ace)}'}, status=503)
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'인증 중 알 수 없는 오류 발생: {str(e)}'}, status=500)

    if request.method == 'POST':
        form = LetterForm(request.POST, request.FILES)
        if form.is_valid():
            letter = form.save(commit=False)
            letter.user_id = user_id_from_token
            letter.category = 'future'

            try:
                letter.save()
                print(f"💾 편지 작성: 편지 저장 완료! (ID: {letter.id}, User: {letter.user_id})")

                image_upload_failed = False

                # 이미지가 있는 경우 업로드 시도
                if request.FILES.get('image'):
                    print("🖼️ 편지 작성: 이미지 파일 감지됨. letter-storage-service에 업로드 시도...")
                    file_to_upload = request.FILES['image']
                    gcs_blob_name_for_letter = upload_image_to_storage(file_to_upload, letter.id)
                    
                    if gcs_blob_name_for_letter:
                        letter.image_url = gcs_blob_name_for_letter
                        print(f"🖼️✅ 편지 작성: 이미지 업로드 성공. Blob Name: {gcs_blob_name_for_letter}")
                    else:
                        # 이미지 업로드 실패 시 로깅 (편지는 이미지 없이 저장됨)
                        print(f"🖼️❌ 편지 작성: 이미지 업로드 실패. 이미지는 저장되지 않습니다.")
                        letter.image_url = None # 또는 빈 문자열로 명시적 설정
                        image_upload_failed = True

                if image_upload_failed:
                    letter.delete()
                    print(f"🗑️ 이미지 업로드 실패로 편지 삭제됨 (ID: {letter.id})")
                    return render(request, 'letters/writing.html', {
                        'form': form,
                        'error_message': '이미지 업로드에 실패하여 편지가 저장되지 않았습니다.'
                    })

                # RabbitMQ 메시지 발행
                if letter.id and letter.user_id and letter.content:
                    print(f"🐰 편지 작성: RabbitMQ로 감정 분석 요청 발행 시도... (편지 ID: {letter.id}, 유저 ID: {letter.user_id})")
                    publish_success = publish_emotion_analysis_request(
                        letter_id=letter.id,
                        user_id=letter.user_id,
                        content=letter.content
                    )
                    if not publish_success:
                        print(f"⚠️ 편지 작성: RabbitMQ 메시지 발행 실패! (편지 ID: {letter.id})")
                else:
                    missing_parts = []
                    if not letter.id: missing_parts.append("ID")
                    if not letter.user_id: missing_parts.append("유저 ID")
                    if not letter.content: missing_parts.append("내용")
                    print(f"ℹ️ 편지 작성: RabbitMQ 메시지 발행 건너뜀 ({', '.join(missing_parts)} 누락). 편지 ID: {letter.id if letter.id else '미정의'}")

                return redirect('letters:letter_list')

            except Exception as e:
                print(f"❌ 편지 작성: 편지 저장 또는 후속 처리 중 오류 발생! - {e}")
                return render(request, 'letters/writing.html', {
                    'form': form,
                    'error_message': '편지 저장 중 오류가 발생했습니다.'
                })

        else:
            print(f"📝❌ 편지 작성: 폼 유효성 검사 실패! 오류: {form.errors.as_json()}")
            return render(request, 'letters/writing.html', {'form': form})
    else:
        form = LetterForm()
    
    return render(request, 'letters/writing.html', {'form': form})



# 2️⃣ 작성된 편지 목록 보기
# @login_required(login_url='/auth/login/') # 로그인 안 된 경우 이 URL로 리디렉션
@csrf_exempt
def letter_list(request):

    # 1. 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("🔑 편지 목록: Authorization 헤더 누락 또는 Bearer 타입 아님.")
        # 여기서는 로그인 페이지로 리디렉션하거나, 에러 페이지를 보여줄 수 있습니다.
        # API라면 JsonResponse를 반환합니다. 여기서는 HTML을 렌더링하므로,
        # 로그인 페이지 URL이 있다면 거기로 보내거나, 접근 거부 페이지를 보여줍니다.
        # return redirect('accounts:login') # 예시: 로그인 페이지로
        return HttpResponseForbidden("인증되지 않은 사용자입니다. 로그인이 필요합니다.")

    token = auth_header.split(' ')[1]
    user_id_from_token = None

    try:
        user_id_from_token = verify_access_token(token)
        logger.info(f"👤 편지 목록: 인증된 사용자 ID {user_id_from_token} 확인")
    except (TokenVerificationFailed, AuthServiceConnectionError, ValueError) as auth_exc: # 인증 관련 예외 통합 처리
        logger.warning(f"🚫 편지 목록: 인증 실패 또는 서비스 오류 - {auth_exc}")
        return HttpResponseForbidden(f"인증에 실패했습니다: {auth_exc}")
    except Exception as e:
        logger.error(f"🤷 편지 목록: 인증 중 알 수 없는 오류 - {e}", exc_info=True)
        return HttpResponseForbidden(f"인증 중 알 수 없는 오류 발생: {str(e)}")

    # --- 인증된 사용자의 편지 목록 조회 ---
    letters_qs = Letters.objects.filter(user_id=user_id_from_token)
    logger.info(f"� 편지 목록: User ID '{user_id_from_token}'의 편지 {letters_qs.count()}개 조회.")

    today = datetime.now().date()

    # 카테고리 업데이트 로직 (이 부분은 성능을 위해 다른 방식으로 처리하는 것을 고려할 수 있습니다)
    for letter_item in letters_qs:
        original_category = letter_item.category
        if letter_item.open_date == today:
            letter_item.category = 'today'
        elif letter_item.open_date > today:
            letter_item.category = 'future'
        else:
            letter_item.category = 'past'
        
        if original_category != letter_item.category:
            letter_item.save()

    return render(request, 'letters/letter_list.html', {'letters': letters_qs})

# 개별 편지 상세보기 api
# @login_required(login_url='/auth/login/')
def letter_json(request, letter_id):

    # 1. 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("🔑 편지 상세: Authorization 헤더 누락 또는 Bearer 타입 아님.")
        return JsonResponse({'error': 'Authorization 헤더가 Bearer 토큰 형식으로 필요합니다.'}, status=401)
    
    token = auth_header.split(' ')[1]
    user_id_from_token = None
    try:
        user_id_from_token = verify_access_token(token)
        logger.info(f"👤 편지 상세: 인증된 사용자 ID {user_id_from_token} 확인 ")
    except (TokenVerificationFailed, AuthServiceConnectionError, ValueError) as auth_exc:
        logger.warning(f"🚫 편지 상세: 인증 실패 또는 서비스 오류 - {auth_exc}")
        return JsonResponse({'error': str(auth_exc)}, status=401)
    except Exception as e:
        logger.error(f"🤷 편지 상세: 인증 중 알 수 없는 오류 - {e}", exc_info=True)
        return JsonResponse({'error': f'인증 중 알 수 없는 오류 발생: {str(e)}'}, status=500)

    # --- 인증된 사용자의 특정 편지 조회 ---
    try:
        letter = get_object_or_404(Letters, id=letter_id, user_id=user_id_from_token)
        logger.info(f"🔍 편지 상세 API: 편지 ID {letter_id} (소유자 ID : {user_id_from_token}) 조회 시도...")
    except Letters.DoesNotExist: # 모델 이름 일관성 유지
        logger.warning(f"❌ 편지 상세 API: 편지 ID {letter_id} (소유자 ID '{user_id_from_token}')를 찾을 수 없습니다.")
        return JsonResponse({'error': '해당 편지를 찾을 수 없거나 접근 권한이 없습니다.'}, status=404)


    signed_url_from_api = None
    if letter.image_url:
        logger.info(f"🖼️ 편지 상세 API: 이미지 blob '{letter.image_url}'에 대한 서명된 URL 요청 시도...")
        signed_url_from_api = get_signed_url_from_storage(letter.image_url)
    else:
        logger.info("ℹ️ 편지 상세 API: 편지에 이미지가 없습니다.")


    data = {
        'id':letter.id,
        'title': letter.title,
        'content': letter.content,
        'letter_date': letter.open_date.strftime("%Y-%m-%d"), #개봉 가능 날짜
        'image_url': signed_url_from_api # API로부터 받은 서명된 URL
    }
    logger.info(f"✅ 편지 상세 API: 편지 ID {letter.id} 데이터 준비 완료.")
    return JsonResponse(data)


# 4️⃣ 편지 삭제 API (내부 API)
# @csrf_exempt # 실제 API로 분리 시 CSRF 처리 방식 변경 필요 (예: Token Authentication)
# @login_required # 로그인 필요
@require_http_methods(["DELETE"]) # DELETE 요청만 허용
def delete_letter_api_internal(request, letter_id):
   # 1. 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("🔑 편지 삭제: Authorization 헤더 누락 또는 Bearer 타입 아님.")
        return JsonResponse({'error': 'Authorization 헤더가 Bearer 토큰 형식으로 필요합니다.'}, status=401)
    
    token = auth_header.split(' ')[1]
    user_id_from_token = None
    try:
        user_id_from_token = verify_access_token(token)
        logger.info(f"👤 편지 삭제: 인증된 사용자 ID {user_id_from_token} 확인 ")
    except (TokenVerificationFailed, AuthServiceConnectionError, ValueError) as auth_exc:
        logger.warning(f"🚫 편지 삭제: 인증 실패 또는 서비스 오류 - {auth_exc}")
        return JsonResponse({'error': str(auth_exc)}, status=401)
    except Exception as e:
        logger.error(f"🤷 편지 삭제: 인증 중 알 수 없는 오류 - {e}", exc_info=True)
        return JsonResponse({'error': f'인증 중 알 수 없는 오류 발생: {str(e)}'}, status=500)

    # --- 인증된 사용자의 특정 편지 삭제 ---
    try:
        letter = get_object_or_404(Letters, id=letter_id, user_id=user_id_from_token) # 🔥 사용자로 필터링 추가!
        logger.info(f"🗑️ 편지 삭제 API: 편지 ID {letter_id} (소유자 ID : {user_id_from_token}) 삭제 시도...")
        
        image_blob_name_to_delete = letter.image_url
        letter.delete()
        logger.info(f"🗑️✅ 편지 삭제 API: DB에서 편지 ID {letter_id} 삭제 완료.")

        if image_blob_name_to_delete:
            logger.info(f"🖼️🗑️ 편지 삭제 API: 스토리지에서 이미지 '{image_blob_name_to_delete}' 삭제 시도...")
            delete_success = delete_image_from_storage(image_blob_name_to_delete)
            if delete_success:
                logger.info(f"🖼️🗑️✅ 편지 삭제 API: 스토리지에서 이미지 '{image_blob_name_to_delete}' 삭제 성공.")
            else:
                logger.warning(f"🖼️🗑️❌ 편지 삭제 API: 스토리지에서 이미지 '{image_blob_name_to_delete}' 삭제 실패 또는 이미 없음.")
        else:
            logger.info("ℹ️ 편지 삭제 API: 편지에 삭제할 이미지가 없습니다.")
            
        return JsonResponse({'status': 'success', 'message': '편지가 성공적으로 삭제되었습니다.'}, status=200)
    
    except Letters.DoesNotExist: # Model명 수정: Letters -> Letter
        print(f"❌ 편지 삭제 API: 편지 ID {letter_id}를 찾을 수 없습니다 (404).")
        return JsonResponse({'status': 'error', 'message': '해당 편지를 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        logger.error(f"❌ 편지 삭제 API: 편지 ID {letter_id} 삭제 중 예상치 못한 오류 발생! {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': '편지 삭제 중 오류가 발생했습니다.'}, status=500)
