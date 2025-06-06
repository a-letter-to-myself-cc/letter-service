from django.urls import path
from . import views
# from django.conf.urls.static import static
# from django.conf import settings


app_name = "letters" 
urlpatterns = [
    path('write/', views.write_letter_api, name="write_letter_api"), # letters/write
    path('', views.letter_list_api, name='letter_list_api'),  # 작성한 편지 목록 letters/
    path('api/letters/<int:letter_id>/', views.letter_api, name="letter_api"),
    path('delete/<int:letter_id>/', views.delete_letter_api_internal, name='delete_letter_api_internal'), # 편지 삭제 API 엔드포인트 (내부 API)
    path('health/', views.health_check),

] 

# # 개발 중일 때만 미디어 파일 서빙
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

