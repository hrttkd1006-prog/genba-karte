from django import forms
from .models import JobPost, HospitalAdminApplication
from hospitals.models import Hospital


class HospitalRegisterForm(forms.ModelForm):
    agreed_to_terms = forms.BooleanField(
        label='利用規約・プライバシーポリシーに同意する',
        error_messages={'required': '利用規約への同意が必要です。'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    phone = forms.CharField(
        label='電話番号',
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '例：03-1234-5678'}),
    )

    class Meta:
        model = HospitalAdminApplication
        fields = ['facility_name', 'contact_name', 'email', 'phone', 'official_url', 'message', 'agreed_to_terms']
        labels = {
            'facility_name': '施設名',
            'contact_name': '担当者名',
            'email': 'メールアドレス',
            'official_url': '施設の公式サイトURL',
            'message': 'その他ご要望・備考（任意）',
        }
        widgets = {
            'facility_name': forms.TextInput(attrs={'placeholder': '例：○○大学病院 検査部'}),
            'contact_name': forms.TextInput(attrs={'placeholder': '例：山田 太郎'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@hospital.jp'}),
            'official_url': forms.URLInput(attrs={'placeholder': 'https://www.example-hospital.jp'}),
            'message': forms.Textarea(attrs={'rows': 3}),
        }


class HospitalAdminApplyForm(forms.Form):
    hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.all().order_by('prefecture', 'name'),
        label='担当施設',
        empty_label='施設を選択してください',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='一覧にない施設は「施設名が見つからない場合」欄に入力してください。',
    )
    hospital_name_new = forms.CharField(
        label='施設名が見つからない場合（新規追加依頼）',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '例：○○大学病院 検査部'}),
    )
    contact_name = forms.CharField(label='ご担当者名', max_length=100)
    contact_email = forms.EmailField(label='ご連絡先メールアドレス')
    message = forms.CharField(
        label='その他ご要望・備考',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def clean(self):
        cleaned = super().clean()
        hospital = cleaned.get('hospital')
        new_name = cleaned.get('hospital_name_new', '').strip()
        if not hospital and not new_name:
            raise forms.ValidationError('施設を選択するか、施設名を入力してください。')
        return cleaned


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['title', 'employment_type', 'salary_min', 'salary_max',
                  'description', 'requirements', 'benefits', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '例：臨床検査技師 募集'}),
            'salary_min': forms.NumberInput(attrs={'placeholder': '例: 350'}),
            'salary_max': forms.NumberInput(attrs={'placeholder': '例: 500'}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'requirements': forms.Textarea(attrs={'rows': 3}),
            'benefits': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'title': '求人タイトル',
            'employment_type': '雇用形態',
            'salary_min': '年収下限（万円）',
            'salary_max': '年収上限（万円）',
            'description': '仕事内容',
            'requirements': '応募条件',
            'benefits': '福利厚生',
            'is_active': '掲載中にする',
        }
