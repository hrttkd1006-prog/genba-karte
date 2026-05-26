from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Review, WORK_STYLE_CHOICES, ONCALL_FREQUENCY_CHOICES, OPPORTUNITY_CHOICES

YEAR_CHOICES = [('', '年')] + [(y, f'{y}年') for y in range(2024, 1989, -1)]
MONTH_CHOICES = [('', '月')] + [(m, f'{m}月') for m in range(1, 13)]
RATING_CHOICES = [(i, '★' * i) for i in range(1, 6)]
DETAIL_RATING_CHOICES = [('', '未回答')] + [(i, f'{i}') for i in range(1, 6)]


class ReviewForm(forms.ModelForm):
    overall_rating = forms.ChoiceField(
        label='総合評価',
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'star-radio'})
    )
    salary_rating = forms.ChoiceField(label='給与', choices=DETAIL_RATING_CHOICES, required=False)
    relationship_rating = forms.ChoiceField(label='人間関係', choices=DETAIL_RATING_CHOICES, required=False)
    education_rating = forms.ChoiceField(label='教育体制', choices=DETAIL_RATING_CHOICES, required=False)
    equipment_rating = forms.ChoiceField(label='設備・機器', choices=DETAIL_RATING_CHOICES, required=False)
    tenure_start_year = forms.ChoiceField(label='在籍開始', choices=YEAR_CHOICES, required=False)
    tenure_start_month = forms.ChoiceField(label='', choices=MONTH_CHOICES, required=False)
    tenure_end_year = forms.ChoiceField(label='在籍終了', choices=YEAR_CHOICES, required=False)
    tenure_end_month = forms.ChoiceField(label='', choices=MONTH_CHOICES, required=False)
    agreed_to_terms = forms.BooleanField(
        label='この内容は実際の経験に基づく事実・意見です',
        required=True
    )
    agreed_to_legal = forms.BooleanField(
        label='虚偽の内容は法的責任を負う可能性があることを理解しています',
        required=True
    )

    class Meta:
        model = Review
        fields = [
            'overall_rating',
            'salary_rating', 'relationship_rating', 'education_rating', 'equipment_rating',
            'annual_salary', 'overtime_hours', 'paid_leave_rate', 'technician_count',
            'has_oncall', 'has_night_duty', 'has_night_shift',
            'has_blood_sampling',
            'work_style', 'night_duty_frequency', 'oncall_frequency',
            'male_ratio', 'average_age',
            'education_system', 'equipment_age', 'employment_type',
            'research_opportunity', 'certification_support',
            'tenure_start_year', 'tenure_start_month',
            'tenure_end_year', 'tenure_end_month', 'is_current',
            'good_points', 'concerns', 'suitable_for',
            'joining_gap',
            'agreed_to_terms',
        ]
        widgets = {
            'annual_salary': forms.NumberInput(attrs={'placeholder': '例: 400', 'min': 0, 'max': 9999}),
            'overtime_hours': forms.NumberInput(attrs={'placeholder': '例: 20', 'min': 0, 'max': 300}),
            'paid_leave_rate': forms.NumberInput(attrs={'placeholder': '例: 60', 'min': 0, 'max': 100}),
            'technician_count': forms.NumberInput(attrs={'placeholder': '例: 15', 'min': 1}),
            'good_points': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': '検査機器が充実していました...'}),
            'concerns': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': '残業が多い月もありました...'}),
            'suitable_for': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'スキルアップを目指す方に...'}),
            'joining_gap': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': '入職前に聞いていた話と実際に違ったことがあれば...'}),
            'male_ratio': forms.HiddenInput(),
            'average_age': forms.NumberInput(attrs={'placeholder': '例: 35', 'min': 20, 'max': 70}),
        }
        labels = {
            'annual_salary': '年収（万円）',
            'overtime_hours': '月の残業時間（時間）',
            'paid_leave_rate': '有給取得率（%）',
            'technician_count': '技師の人数（人）',
            'has_oncall': 'オンコールあり',
            'has_night_duty': '当直あり',
            'has_night_shift': '夜勤あり',
            'has_blood_sampling': '採血行為あり',
            'work_style': '業務スタイル',
            'night_duty_frequency': '当直の頻度',
            'oncall_frequency': 'オンコールの頻度',
            'male_ratio': '技師の男女比',
            'average_age': '技師の平均年齢（歳）',
            'education_system': '教育体制',
            'equipment_age': '機器の新しさ',
            'employment_type': '雇用形態',
            'research_opportunity': '学会発表・研究の機会',
            'certification_support': '認定資格のサポート',
            'is_current': '現在も在籍中',
            'good_points': '良かった点',
            'concerns': '気になった点',
            'suitable_for': 'どんな人に向いている職場か',
            'joining_gap': '入職後のギャップ',
            'agreed_to_terms': '利用規約への同意',
        }

    def clean_overall_rating(self):
        return int(self.cleaned_data['overall_rating'])

    def clean(self):
        cleaned = super().clean()
        for field in ['tenure_start_year', 'tenure_start_month', 'tenure_end_year', 'tenure_end_month']:
            val = cleaned.get(field)
            cleaned[field] = int(val) if val else None
        for field in ['salary_rating', 'relationship_rating', 'education_rating', 'equipment_rating']:
            val = cleaned.get(field)
            cleaned[field] = int(val) if val else None
        return cleaned
