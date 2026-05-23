from django import forms
from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['handle_name', 'workplace']
        labels = {
            'handle_name': 'ハンドル名',
            'workplace': '勤務先・学校名（任意）',
        }
        widgets = {
            'handle_name': forms.TextInput(attrs={'placeholder': '例：けんさ太郎、MT_osaka'}),
            'workplace': forms.TextInput(attrs={'placeholder': '例：○○大学病院、△△検査センター'}),
        }
