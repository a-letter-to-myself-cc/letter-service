from rest_framework import serializers
from .models import Letters

class LetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Letters
        fields = ['id', 'user_id', 'title', 'content', 'created_at', 'open_date', 'image_url', 'category', 'mood', 'detailed_mood']
        read_only_fields = ['id', 'user_id', 'created_at'] # user_id는 요청 시 직접 받지 않고 인증 통해 설정

class LetterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Letters
        fields = ['title', 'content', 'open_date', 'image_url', 'category'] 
        extra_kwargs = {
            'image_url': {'required': False, 'allow_null': True}
        }