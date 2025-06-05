from django.shortcuts import get_object_or_404
from .models import Letters
from .serializers import LetterSerializer, LetterCreateSerializer
from datetime import datetime
from django.conf import settings
from rest_framework.decorators import api_view # DRF 데코레이터
from rest_framework.response import Response # DRF의 Response 객체
from rest_framework import status # HTTP 상태 코드

# 스토리지, 토큰, 이모션 파일들 임포트
from .storage_client import upload_image_to_storage, get_signed_url_from_storage, delete_image_from_storage
from .auth_client import verify_access_token
from .message_producers import publish_emotion_analysis_request

# 편지 작성 뷰
@api_view(['POST'])
def write_letter_api(request):

    # 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'detail': 'Authorization header missing or malserializered'}, status=401)
    token = auth_header.split("Bearer ")[1]
    try:
        user_id = verify_access_token(token)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)

    serializer = LetterCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            letter = serializer.save(user_id=user_id, category='future')  # ✅ 데이터 저장 전에 추가 설정
            print(f"💾 편지 작성: 편지 저장 완료! (ID: {letter.id}, User: {letter.user_id})")

            # 이미지 업로드 성공/실패 여부를 나타내는 변수(롤백을 위해 사용)
            image_upload_failed = False

            gcs_blob_name_for_letter = None

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
                return Response(
                    {"error": "이미지 업로드에 실패하여 편지가 저장되지 않았습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # RabbitMQ로 감정 분석 요청 발행 (user_id 포함)
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
                
            response_serializer = LetterSerializer(letter) 
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e: # letter.save() 또는 그 이후 과정에서 발생할 수 있는 예외 처리
            print(f"❌ 편지 작성: 편지 저장 또는 후속 처리 중 오류 발생! - {e}")
            return Response({'error': '편지 저장 중 서버 내부 오류가 발생했습니다.', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else: # serializer.is_valid()가 False일 때
        print(f"📝❌ 편지 작성: 폼 유효성 검사 실패! 오류: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# 2️⃣ 작성된 편지 목록 보기
@api_view(['GET'])
def letter_list_api(request):

    # 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'detail': 'Authorization header missing or malformed'}, status=401)
    token = auth_header.split("Bearer ")[1]
    try:
        user_id = verify_access_token(token)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)

    # --- 인증된 사용자의 편지 목록 조회 ---
    letters_qs = Letters.objects.filter(user_id=user_id)
    print(f"� 편지 목록: User ID '{user_id}'의 편지 {letters_qs.count()}개 조회.")

    today = datetime.now().date()

    # 카테고리 업데이트 로직
    letters_to_update = []
    for letter_item in letters_qs:
        original_category = letter_item.category
        new_category = original_category

        if letter_item.open_date == today:
            new_category = 'today'
        elif letter_item.open_date > today:
            new_category = 'future'
        else:
            new_category = 'past'
        
        if original_category != new_category:
            letter_item.category = new_category
            letters_to_update.append(letter_item) # 변경된 편지만 리스트에 추가

    # LetterSerializer를 사용하여 편지 목록 데이터를 직렬화
    serializer = LetterSerializer(letters_qs, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)


# 개별 편지 상세보기 api
@api_view(['GET'])
def letter_api(request, letter_id):

    # 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'detail': 'Authorization header missing or malformed'}, status=401)
    token = auth_header.split("Bearer ")[1]
    try:
        user_id = verify_access_token(token)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)

    # --- 인증된 사용자의 특정 편지 조회 ---
    letter = get_object_or_404(Letters, id=letter_id, user_id=user_id)
    print(f"🔍 편지 상세 API: 편지 ID {letter_id} (소유자 ID : {user_id}) 조회 성공.")

    serializer = LetterSerializer(letter)
    response_data = serializer.data # 직렬화된 데이터 가져오기

    # signed_url_from_api = None --> Serializer가 blob 이름을 반환한다고 바꿈
    if letter.image_url:
        print(f"🖼️ 편지 상세 API: 이미지 blob '{letter.image_url}'에 대한 서명된 URL 요청 시도...")
        signed_url_from_api = get_signed_url_from_storage(letter.image_url)
        response_data['image_url'] = signed_url_from_api # 직렬화된 데이터의 image_url 값을 서명된 URL로 덮어쓰기
        if signed_url_from_api:
            print(f"🖼️✅ 편지 상세 API: 서명된 URL 생성 성공.")
        else:
            print(f"🖼️❌ 편지 상세 API: 서명된 URL 생성 실패.")
    else:
        print("ℹ️ 편지 상세 API: 편지에 이미지가 없습니다.")
        response_data['image_url'] = None # 이미지가 없는 경우 명시적으로 None 설정

    print(f"✅ 편지 상세 API: 편지 ID {letter.id} 데이터 준비 완료.")
    return Response(response_data, status=status.HTTP_200_OK)


# 4️⃣ 편지 삭제 API (내부 API)
@api_view(["DELETE"]) # DELETE 요청만 허용
def delete_letter_api_internal(request, letter_id):
    # 토큰 추출 및 사용자 인증
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'detail': 'Authorization header missing or malformed'}, status=401)
    token = auth_header.split("Bearer ")[1]
    try:
        user_id = verify_access_token(token)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)

    # --- 인증된 사용자의 특정 편지 삭제 ---
    try:
        letter = Letters.objects.get(id=letter_id, user_id=user_id)
        print(f"🗑️ 편지 삭제 API: 편지 ID {letter_id} (소유자 ID : {user_id}) 삭제 시도...")
        
        image_blob_name_to_delete = letter.image_url
        letter.delete()
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
            
        return Response({'status': 'success', 'message': '편지가 성공적으로 삭제되었습니다.'}, status=200)
    
    except Letters.DoesNotExist:
        print(f"❌ 편지 삭제 API: 편지 ID {letter_id} (소유자 ID : {user_id})를 찾을 수 없거나 권한이 없습니다.")
        return Response({'status': 'error', 'message': '해당 편지를 찾을 수 없거나 삭제 권한이 없습니다.'}, status=404)
    except Exception as e:
        print(f"❌ 편지 삭제 API: 편지 ID {letter_id} 삭제 중 예상치 못한 오류 발생! {e}", exc_info=True)
        return Response({'status': 'error', 'message': '편지 삭제 중 오류가 발생했습니다.'}, status=500)
