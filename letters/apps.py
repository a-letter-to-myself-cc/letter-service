from django.apps import AppConfig

class LettersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'letters' # -> 마이크로서비스일때

    def ready(self):
        from letters.models import Letters  # ✅ 강제로 models.py 로드