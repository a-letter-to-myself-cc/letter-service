from django.db import models
from django.utils.timezone import now
from django.core.exceptions import ImproperlyConfigured


CATEGORIES = (
    ('past','과거'),
     ('today','오늘'),
     ('future','미래'),
)

MOOD_CHOICES = [
    ('joy', '기쁨'),         # 희열, 만족, 감사, 설렘 포함
    ('sadness', '슬픔'),     # 외로움, 상실감, 후회 포함
    ('anger', '분노'),       # 짜증, 분개, 억울함 포함
    ('anxiety', '불안'),     # 두려움, 긴장, 초조 포함
    ('love', '사랑'),        # 로맨스, 우정, 존경 포함
    ('neutral', '중립'),     # 감정 없음 또는 평온한 상태
]
# 세부 감정
DETAILED_MOOD_CHOICES = [
    # 기쁨
    ('ecstasy', '희열'),
    ('satisfaction', '만족'),
    ('gratitude', '감사'),
    ('excitement', '설렘'),
    # 슬픔
    ('loneliness', '외로움'),
    ('loss', '상실감'),
    ('regret', '후회'),
    # 분노
    ('annoyance', '짜증'),
    ('rage', '분개'),
    ('resentment', '억울함'),
    # 불안
    ('fear', '두려움'),
    ('nervousness', '긴장'),
    ('restlessness', '초조'),
    # 사랑
    ('romance', '로맨스'),
    ('friendship', '우정'),
    ('respect', '존경'),
]


# Create your models here.
class Letters(models.Model):
    user_id = models.IntegerField() #(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="letters")  # auth에서 커스텀해놓은 user 모델 사용
    id = models.AutoField(primary_key=True)  # 기본 키 설정
    title = models.CharField(max_length=200)  # 편지 제목
    content = models.TextField()  # 편지 내용
    image_url = models.URLField(null=True, blank=True) # 이미지 url 저장(gcs 연동)
    created_at = models.DateTimeField(auto_now_add=True)  # 작성 시간
    open_date = models.DateField()  # 편지를 열 수 있는 날짜 (선택)
    category = models.CharField(max_length=20,
                                choices=CATEGORIES,
                                default='future')
    mood = models.CharField(max_length=30, choices=MOOD_CHOICES, null=True, blank=True)
    detailed_mood = models.CharField(max_length=30, choices=DETAILED_MOOD_CHOICES, blank=True, null=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    # mood = models.CharField(max_length=10, choices=MOOD_CHOICES, default='happy')

    def save(self, *args, **kwargs):
        """ 개봉 일자에 따라 자동으로 카테고리 설정 """
        today = now().date()

        if self.open_date < today:
            self.category = 'past'  # 개봉일이 지났다면 과거
        elif self.open_date == today:
            self.category = 'today'  # 개봉일이 오늘이라면 오늘
        else:
            self.category = 'future'  # 개봉일이 아직 안 됐다면 미래

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.category}"
    
    class Meta:
        app_label = 'letters'