"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings


app_name = "letters" 
urlpatterns = [
    path('write/', views.write_letter, name="writing"), # letters/write
    path('', views.letter_list, name='letter_list'),  # 작성한 편지 목록 letters/
    path('api/letters/<int:letter_id>/', views.letter_json, name="letter_json"),
    path('delete/<int:letter_id>/', views.delete_letter_api_internal, name='delete_letter_api_internal'), # 편지 삭제 API 엔드포인트 (내부 API)
] 

# 개발 중일 때만 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

