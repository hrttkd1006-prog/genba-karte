from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


EMPLOYMENT_TYPE_CHOICES = [
    ('full_time', '常勤'),
    ('part_time', 'パート'),
    ('dispatch', '派遣'),
]

EDUCATION_CHOICES = [
    ('good', '充実している'),
    ('average', '普通'),
    ('poor', 'ほぼない'),
]

EQUIPMENT_CHOICES = [
    ('new', '新しい'),
    ('average', '普通'),
    ('old', '古い'),
]

WORK_STYLE_CHOICES = [
    ('specialized', '専門特化型（特定部署のみ）'),
    ('rotation', 'ローテーション型（全検査を幅広く）'),
    ('partial', '一部ローテーション（専門＋一部兼任）'),
]

ONCALL_FREQUENCY_CHOICES = [
    ('none', 'なし'),
    ('less_monthly', '月1回未満'),
    ('monthly_1_3', '月1〜3回'),
    ('weekly_1_2', '週1〜2回'),
    ('weekly_3_plus', '週3回以上'),
]

OPPORTUNITY_CHOICES = [
    ('good', '充実している'),
    ('sometimes', 'たまにある'),
    ('rarely', 'ほぼない'),
]

REVIEW_STATUS_CHOICES = [
    ('pending', '審査中'),
    ('approved', '公開'),
    ('rejected', '非公開'),
    ('objection', '確認中（異議申し立て）'),
]

AI_JUDGMENT_CHOICES = [
    ('white', '問題なし'),
    ('gray', '要確認'),
    ('black', '非公開'),
]


class Review(models.Model):
    hospital = models.ForeignKey(
        'hospitals.Hospital', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='病院・施設'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='reviews', verbose_name='投稿者'
    )
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)

    # 数値・選択式
    annual_salary = models.PositiveIntegerField('年収（万円）', null=True, blank=True)
    overtime_hours = models.PositiveSmallIntegerField('月残業時間', null=True, blank=True)
    paid_leave_rate = models.PositiveSmallIntegerField('有給取得率（%）', null=True, blank=True)
    technician_count = models.PositiveSmallIntegerField('技師の人数', null=True, blank=True)
    has_oncall = models.BooleanField('オンコールあり', default=False)
    has_night_duty = models.BooleanField('当直あり', default=False)
    has_night_shift = models.BooleanField('夜勤あり', default=False)
    has_blood_sampling = models.BooleanField('採血行為あり', null=True, blank=True)
    work_style = models.CharField('業務スタイル', max_length=15, choices=WORK_STYLE_CHOICES, blank=True)
    oncall_night_frequency = models.CharField('オンコール・夜勤の頻度', max_length=15, choices=ONCALL_FREQUENCY_CHOICES, blank=True)
    male_ratio = models.PositiveSmallIntegerField('男性技師の割合（0〜10）', null=True, blank=True)
    average_age = models.PositiveSmallIntegerField('平均年齢', null=True, blank=True)
    research_opportunity = models.CharField('学会発表・研究の機会', max_length=10, choices=OPPORTUNITY_CHOICES, blank=True)
    certification_support = models.CharField('認定資格のサポート', max_length=10, choices=OPPORTUNITY_CHOICES, blank=True)
    joining_gap = models.TextField('入職後のギャップ', blank=True)
    education_system = models.CharField(
        '教育体制', max_length=10, choices=EDUCATION_CHOICES, blank=True
    )
    equipment_age = models.CharField(
        '機器の新しさ', max_length=10, choices=EQUIPMENT_CHOICES, blank=True
    )
    employment_type = models.CharField(
        '雇用形態', max_length=15, choices=EMPLOYMENT_TYPE_CHOICES, blank=True
    )
    tenure_start_year = models.PositiveSmallIntegerField('在籍開始年', null=True, blank=True)
    tenure_start_month = models.PositiveSmallIntegerField('在籍開始月', null=True, blank=True)
    tenure_end_year = models.PositiveSmallIntegerField('在籍終了年', null=True, blank=True)
    tenure_end_month = models.PositiveSmallIntegerField('在籍終了月', null=True, blank=True)
    is_current = models.BooleanField('現在も在籍中', default=False)

    # 評価スコア
    overall_rating = models.PositiveSmallIntegerField('総合評価（1〜5）', default=3)
    salary_rating = models.PositiveSmallIntegerField('給与評価（1〜5）', null=True, blank=True)
    relationship_rating = models.PositiveSmallIntegerField('人間関係評価（1〜5）', null=True, blank=True)
    education_rating = models.PositiveSmallIntegerField('教育体制評価（1〜5）', null=True, blank=True)
    equipment_rating = models.PositiveSmallIntegerField('設備・機器評価（1〜5）', null=True, blank=True)

    # テキスト
    good_points = models.TextField('良かった点')
    concerns = models.TextField('気になった点')
    suitable_for = models.TextField('どんな人に向いている職場か')

    # 同意
    agreed_to_terms = models.BooleanField('利用規約に同意', default=False)

    # 審査
    status = models.CharField('公開状態', max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending')
    ai_judgment = models.CharField('AI判定', max_length=10, choices=AI_JUDGMENT_CHOICES, blank=True)
    ai_reason = models.TextField('AI判定理由', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'レビュー'
        verbose_name_plural = 'レビュー'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.hospital.name} - {self.created_at.strftime('%Y/%m/%d')}"

    @property
    def female_ratio(self):
        if self.male_ratio is not None:
            return 10 - self.male_ratio
        return None

    def get_staleness_label(self):
        now = timezone.now()
        delta = now - self.created_at
        if delta.days >= 365 * 3:
            return 'very_old'
        if delta.days >= 365:
            return 'old'
        return None

    def get_tenure_display(self):
        start = f"{self.tenure_start_year}年{self.tenure_start_month}月" if self.tenure_start_year else ''
        if self.is_current:
            end = '現在'
        elif self.tenure_end_year:
            end = f"{self.tenure_end_year}年{self.tenure_end_month}月"
        else:
            end = ''
        if start and end:
            return f"{start} 〜 {end}"
        return start or end


class ReviewHelpful(models.Model):
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE,
        related_name='helpful_votes', verbose_name='レビュー'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='helpful_votes', verbose_name='ユーザー'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '参考になった'
        verbose_name_plural = '参考になった'
        unique_together = ('review', 'user')

    def __str__(self):
        return f"{self.user.email} → review#{self.review_id}"


class Objection(models.Model):
    STATUS_CHOICES = [
        ('pending', '審査中'),
        ('waiting_reply', '投稿者返答待ち'),
        ('resolved_hide', '非公開処理済み'),
        ('resolved_keep', '公開維持'),
    ]

    review = models.ForeignKey(
        Review, on_delete=models.CASCADE,
        related_name='objections', verbose_name='対象レビュー'
    )
    hospital_name = models.CharField('申立病院名', max_length=200)
    contact_email = models.EmailField('連絡先メール')
    reason = models.TextField('申立理由')
    status = models.CharField('処理状態', max_length=20, choices=STATUS_CHOICES, default='pending')
    reply_deadline = models.DateTimeField('返答期限', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '異議申し立て'
        verbose_name_plural = '異議申し立て'

    def __str__(self):
        return f"{self.review} への異議申し立て"

    def set_reply_deadline(self):
        from django.conf import settings
        hours = getattr(settings, 'OBJECTION_REPLY_HOURS', 72)
        self.reply_deadline = timezone.now() + datetime.timedelta(hours=hours)
        self.save()
