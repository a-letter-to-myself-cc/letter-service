from django import forms
#마이크로서비스
from letters.models import Letters
#모놀리식일때
# from letters_service.letters.models import Letter



class LetterForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    
    class Meta:
        model = Letters
        fields = ['title','content', 'open_date']  # 사용자 입력 필드

        widgets = {
            'content': forms.Textarea(attrs={'class':'form-control', 'style':'width: 350px; height:440px'}),
            'open_date': forms.DateInput(attrs={'type': 'date'}),  # 날짜 입력 필드
            
        }