from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Letters
from .forms import LetterForm
from django.utils.timezone import now  # 현재 날짜 가져오기
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse # 토큰 인증 사용
from datetime import datetime, timedelta
import openai
import os
from django.urls import reverse # 내부 API 호출 URL 생성
from django.conf import settings
from django.contrib.auth.models import User
# 스토리지, 토큰, 이모션 파일들 임포트
from .storage_client import upload_image_to_storage, get_signed_url_from_storage, delete_image_from_storage
from .auth_client import get_user_id_from_token # 위에서 만든 함수 임포트
from .message_producers import publish_emotion_analysis_request

import requests # 외부 API 호출용

# import json # POST, PUT 요청의 JSON 본문을 파싱하기 위해
# import requests # 다른 내부 API (예: 감정 분석) 호출을 위해

openai.api_key = os.getenv("OPENAI_API_KEY")

# 개발용 가짜 유저 주입

from django.contrib.auth import get_user_model

def some_view(request):
    User = get_user_model()

fake_user = User.objects.first()
letters = Letters.objects.filter(user=fake_user)

def home(request):
    # 이 뷰는 'myapp/index.html'을 렌더링하며, letters 서비스의 핵심 HTML 분리와는 별개일 수 있습니다.
    # 새로운 프론트엔드 서비스가 자체 홈페이지를 가질 것이므로, 이 뷰의 역할은 재검토될 수 있습니다.
    # 지금은 그대로 둡니다.
    return render(request, 'myapp/index.html')

# 1️⃣ 편지 작성 뷰
# @login_required(login_url='/auth/login/')  # 👈 직접 로그인 URL 지정 (auth 마이크로서비스)
@csrf_exempt # 테스트를위해 csrf 검사 생략
def write_letter(request):
    #  # 1. 요청 헤더에서 Access Token 추출
    # auth_header = request.headers.get('Authorization') # "Authorization: Bearer <token>" 형식
    # access_token = None

    # if auth_header and auth_header.startswith('Bearer '):
    #     access_token = auth_header.split(' ')[1]
        
    # if not access_token:
    #     print("🔑 편지 뷰: 요청에 Bearer 토큰이 없습니다.")
    #     return JsonResponse({'error': '인증 토큰이 헤더에 Bearer 타입으로 제공되어야 합니다.'}, status=401)

    # # 2. 추출한 토큰으로 user_id 가져오기
    # user_id = get_user_id_from_token(access_token)

    # if user_id is None:
    #     print("🚫 편지 뷰: 유효한 user_id를 얻지 못했습니다. 인증 실패 처리.")
    #     return JsonResponse({'error': '인증에 실패했거나 유효하지 않은 토큰입니다.'}, status=401)
        
    # 개발용 가짜 유저 지정
    fake_user = User.objects.first()
    if not fake_user:
        return JsonResponse({"error:" "테스트 유저 없음"})

    if request.method == 'POST':
        form = LetterForm(request.POST, request.FILES)
        if form.is_valid():
            letter = form.save(commit=False)  # ✅ 데이터 저장 전에 추가 설정
            letter.user = fake_user # 원래는 request.user  # 🔥 작성자를 현재 로그인한 사용자로 설정
            letter.category = 'future' # 기본적으로 미래 카테고리로 분류
            
            gcs_blob_name_for_letter = None

            if request.FILES.get('image'):
                print("🖼️ 편지 작성: 이미지 파일 감지됨. 업로드 시도...")
                file_to_upload = request.FILES['image']
                gcs_blob_name_for_letter = upload_image_to_storage(file_to_upload) # storage_service_client.py의 함수

                if gcs_blob_name_for_letter:
                    letter.image_url = gcs_blob_name_for_letter
                    print(f"🖼️✅ 편지 작성: 이미지 업로드 성공. Blob Name: {gcs_blob_name_for_letter}")
                else:
                    # 이미지 업로드 실패 시 로깅 (편지는 이미지 없이 저장됨)
                    print(f"🖼️❌ 편지 작성: 이미지 업로드 실패. 이미지는 저장되지 않습니다.")
                    letter.image_url = None # 또는 빈 문자열로 명시적 설정

            # 모든 정보가 준비된 후, DB에 최종적으로 한 번만 저장
            try:
                letter.save()
                print(f"💾 편지 작성: 편지 저장 완료! (ID: {letter.id}, User: {letter.user.id})")

                # RabbitMQ로 감정 분석 요청 발행 (user_id 포함)
                # letter.id가 있어야 하고, letter.user(또는 letter.user_id)가 있어야 하고, content가 있어야 함
                if letter.id and letter.user and letter.user.id and letter.content:
                    print(f"🐰 편지 작성: RabbitMQ로 감정 분석 요청 발행 시도... (편지 ID: {letter.id}, 유저 ID: {letter.user.id})")
                    publish_success = publish_emotion_analysis_request(
                        letter_id=letter.id,
                        user_id=letter.user.id,
                        content=letter.content
                    )
                    if not publish_success:
                        print(f"⚠️ 편지 작성: RabbitMQ 메시지 발행 실패! (편지 ID: {letter.id})")
                else:
                    missing_parts = []
                    if not letter.id: missing_parts.append("ID")
                    if not letter.user or not letter.user.id: missing_parts.append("유저 ID")
                    if not letter.content: missing_parts.append("내용")
                    print(f"ℹ️ 편지 작성: RabbitMQ 메시지 발행 건너뜀 ({', '.join(missing_parts)} 누락). 편지 ID: {letter.id if letter.id else '미정의'}")
                
                return redirect('letters:letter_list')

            except Exception as e: # letter.save() 또는 그 이후 과정에서 발생할 수 있는 예외 처리
                print(f"❌ 편지 작성: 편지 저장 또는 후속 처리 중 오류 발생! - {e}")
                # 사용자에게 오류 메시지를 보여주거나, 폼을 다시 보여줄 수 있음
                # form.add_error(None, "편지 저장 중 문제가 발생했습니다. 다시 시도해주세요.") # 폼 에러 추가
                return render(request, 'letters/writing.html', {'form': form, 'error_message': '편지 저장 중 오류가 발생했습니다.'})

        else: # form.is_valid()가 False일 때
            print(f"📝❌ 편지 작성: 폼 유효성 검사 실패! 오류: {form.errors.as_json()}")
            return render(request, 'letters/writing.html', {'form': form}) # 오류 있는 폼 다시 보여주기
    else: # GET 요청일 때
        form = LetterForm()
    
    return render(request, 'letters/writing.html', {'form': form})


# 2️⃣ 작성된 편지 목록 보기
# @login_required(login_url='/auth/login/') # 로그인 안 된 경우 이 URL로 리디렉션
@csrf_exempt
def letter_list(request):

    # 개발용 가짜 유저 지정
    fake_user = User.objects.first()
    if not fake_user:
        return JsonResponse({"error": "테스트용 유저가 없습니다."})
    letters = Letters.objects.filter(user=fake_user)   # 원래는 (user=request.user) 
    print(f"📄 편지 목록: '{fake_user.username}' 유저의 편지 {letters.count()}개 조회.")
    #####

    today = datetime.now().date()
    
    for letter in letters:
        if letter.open_date == today:
            letter.category = 'today'
        elif letter.open_date > today:
            letter.category = 'future'
        else:
            letter.category = 'past'
        letter.save()  # ✅ DB에 저장!


    return render(request, 'letters/letter_list.html', {
        'letters': letters,
    })


# 개별 편지 상세보기 api
# @login_required(login_url='/auth/login/')
def letter_json(request, letter_id):
    print(f"🔍 편지 상세 API: 편지 ID {letter_id} 조회 시도...")
    # letter = get_object_or_404(Letters, id=letter_id, user=request.user) # 로그인 기능 복원 시
    letter = get_object_or_404(Letters, id=letter_id)

    signed_url_from_api = None
    if letter.image_url: # image_url에 GCS 내의 blob_name이 저장되어 있다고 가정
        print(f"🖼️ 편지 상세 API: 이미지 blob '{letter.image_url}'에 대한 서명된 URL 요청 시도...")
        signed_url_from_api = get_signed_url_from_storage(letter.image_url)
    else: {
        print("ℹ️ 편지 상세 API: 편지에 이미지가 없습니다.")
    }    

    data = {
        'id':letter.id,
        'title': letter.title,
        'content': letter.content,
        'letter_date': letter.open_date.strftime("%Y-%m-%d"), #개봉 가능 날짜
        'image_url': signed_url_from_api # API로부터 받은 서명된 URL
    }
    print(f"✅ 편지 상세 API: 편지 ID {letter.id} 데이터 준비 완료.")
    return JsonResponse(data)


# 4️⃣ 편지 삭제 API (내부 API)
@csrf_exempt # 실제 API로 분리 시 CSRF 처리 방식 변경 필요 (예: Token Authentication)
# @login_required # 로그인 필요
@require_http_methods(["DELETE"]) # DELETE 요청만 허용
def delete_letter_api_internal(request, letter_id):
    try:
            # 개발용 가짜 유저 지정
        fake_user = User.objects.first()
        # letter = get_object_or_404(Letters, id=letter_id, user=request.user)
        letter = get_object_or_404(Letters, id=letter_id) # 테스트용 유저 정보 뺀 레터
        image_blob_name_to_delete = letter.image_url # DB에서 편지 삭제 전에 blob 이름 저장

        letter.delete() # DB에서 편지 레코드 삭제
        print(f"🗑️✅ 편지 삭제 API: DB에서 편지 ID {letter_id} 삭제 완료.")

        if image_blob_name_to_delete:
            print(f"🖼️🗑️ 편지 삭제 API: 스토리지에서 이미지 '{image_blob_name_to_delete}' 삭제 시도...")
            delete_success = delete_image_from_storage(image_blob_name_to_delete)
            if delete_success:
                print(f"🖼️🗑️✅ 편지 삭제 API: 스토리지에서 이미지 '{image_blob_name_to_delete}' 삭제 성공.")
            else:
                print(f"🖼️🗑️❌ 편지 삭제 API: 스토리지에서 이미지 '{image_blob_name_to_delete}' 삭제 실패 또는 이미 없음.")
        else:
            print("ℹ️ 편지 삭제 API: 편지에 삭제할 이미지가 없습니다.")
            
        return JsonResponse({'status': 'success', 'message': '편지가 성공적으로 삭제되었습니다.'}, status=200)
    
    except Letters.DoesNotExist: # Model명 수정: Letters -> Letter
        print(f"❌ 편지 삭제 API: 편지 ID {letter_id}를 찾을 수 없습니다 (404).")
        return JsonResponse({'status': 'error', 'message': '해당 편지를 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        print(f"❌ 편지 삭제 API: 편지 ID {letter_id} 삭제 중 예상치 못한 오류 발생! {e}")
        return JsonResponse({'status': 'error', 'message': '편지 삭제 중 오류가 발생했습니다.'}, status=500)