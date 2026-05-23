from django import forms
from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['workplace']
        labels = {'workplace': '勤務先・学校名'}
        widgets = {'workplace': forms.TextInput(attrs={'placeholder': '例：○○大学病院、△△検査センター'})}
