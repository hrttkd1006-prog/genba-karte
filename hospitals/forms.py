from django import forms
from .models import FacilityRequest
from reviews.models import (
    EMPLOYMENT_TYPE_CHOICES, EDUCATION_CHOICES, EQUIPMENT_CHOICES,
    WORK_STYLE_CHOICES, ONCALL_FREQUENCY_CHOICES, OPPORTUNITY_CHOICES,
)

RATING_CHOICES = [(i, '★' * i) for i in range(1, 6)]
DETAIL_RATING_CHOICES = [('', '未回答')] + [(i, f'{i}') for i in range(1, 6)]


class FacilityRequestForm(forms.ModelForm):
    overall_rating = forms.ChoiceField(
        label='総合評価',
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'star-radio'}),
        required=True,
    )
    salary_rating = forms.ChoiceField(label='給与', choices=DETAIL_RATING_CHOICES, required=False)
    relationship_rating = forms.ChoiceField(label='人間関係', choices=DETAIL_RATING_CHOICES, required=False)
    education_rating = forms.ChoiceField(label='教育体制', choices=DETAIL_RATING_CHOICES, required=False)
    equipment_rating = forms.ChoiceField(label='設備・機器', choices=DETAIL_RATING_CHOICES, required=False)

    agreed_to_terms = forms.BooleanField(
        label='この内容は実際の経験に基づく事実・意見です', required=True,
    )
    agreed_to_legal = forms.BooleanField(
        label='虚偽の内容は法的責任を負う可能性があることを理解しています', required=True,
    )

    class Meta:
        model = FacilityRequest
        fields = [
            'facility_name', 'prefecture', 'address', 'facility_type',
            'overall_rating',
            'salary_rating', 'relationship_rating', 'education_rating', 'equipment_rating',
            'annual_salary', 'overtime_hours', 'paid_leave_rate', 'technician_count',
            'employment_type', 'education_system', 'equipment_age',
            'has_oncall', 'has_night_duty', 'has_night_shift', 'has_blood_sampling',
            'work_style', 'oncall_night_frequency',
            'male_ratio', 'average_age',
            'research_opportunity', 'certification_support',
            'good_points', 'concerns', 'suitable_for', 'joining_gap',
        ]
        widgets = {
            'facility_name': forms.TextInput(attrs={'placeholder': '例: 大阪大学医学部附属病院'}),
            'address': forms.TextInput(attrs={'placeholder': '例: 大阪府吹田市山田丘2-15（任意）'}),
            'annual_salary': forms.NumberInput(attrs={'placeholder': '例: 400', 'min': 0}),
            'overtime_hours': forms.NumberInput(attrs={'placeholder': '例: 20', 'min': 0}),
            'paid_leave_rate': forms.NumberInput(attrs={'placeholder': '例: 60', 'min': 0, 'max': 100}),
            'technician_count': forms.NumberInput(attrs={'placeholder': '例: 15', 'min': 1}),
            'average_age': forms.NumberInput(attrs={'placeholder': '例: 35', 'min': 20, 'max': 70}),
            'male_ratio': forms.HiddenInput(),
            'good_points': forms.Textarea(attrs={'rows': 4, 'placeholder': '検査機器が充実していました...'}),
            'concerns': forms.Textarea(attrs={'rows': 4, 'placeholder': '残業が多い月もありました...'}),
            'suitable_for': forms.Textarea(attrs={'rows': 3, 'placeholder': 'スキルアップを目指す方に...'}),
            'joining_gap': forms.Textarea(attrs={'rows': 3, 'placeholder': '入職前に聞いていた話と実際に違ったことがあれば...'}),
        }
        labels = {
            'facility_name': '施設名', 'prefecture': '都道府県',
            'address': '住所（任意）', 'facility_type': '施設種別',
            'annual_salary': '年収（万円）', 'overtime_hours': '月の残業時間（時間）',
            'paid_leave_rate': '有給取得率（%）', 'technician_count': '技師の人数（人）',
            'employment_type': '雇用形態', 'education_system': '教育体制',
            'equipment_age': '機器の新しさ', 'work_style': '業務スタイル',
            'oncall_night_frequency': 'オンコール・夜勤の頻度',
            'male_ratio': '技師の男女比', 'average_age': '技師の平均年齢（歳）',
            'research_opportunity': '学会発表・研究の機会',
            'certification_support': '認定資格のサポート',
            'has_oncall': 'オンコールあり', 'has_night_duty': '当直あり',
            'has_night_shift': '夜勤あり', 'has_blood_sampling': '採血行為あり',
            'good_points': '良かった点', 'concerns': '気になった点',
            'suitable_for': 'どんな人に向いている職場か', 'joining_gap': '入職後のギャップ',
        }

    def clean_overall_rating(self):
        return int(self.cleaned_data['overall_rating'])

    def clean(self):
        cleaned = super().clean()
        for field in ['salary_rating', 'relationship_rating', 'education_rating', 'equipment_rating']:
            val = cleaned.get(field)
            cleaned[field] = int(val) if val else None
        return cleaned
