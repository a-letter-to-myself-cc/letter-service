from django.apps import AppConfig

class LettersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'letters' # -> 마이크로서비스일때
    #모놀리식일때
    # name = 'letters_service.letters'

    def ready(self):
        # 마이크로서비스일때
        from letters.models import Letters  # ✅ 강제로 models.py 로드

        #모놀리식일때
        # from letters_service.letters.models import Letter