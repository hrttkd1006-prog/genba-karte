from django.db import models
from django.conf import settings


EMPLOYMENT_TYPE_CHOICES = [
    ('full_time', '常勤'),
    ('part_time', 'パート'),
    ('dispatch', '派遣'),
    ('contract', '契約社員'),
]

SUBSCRIPTION_STATUS_CHOICES = [
    ('inactive', '未契約'),
    ('active', '掲載中'),
    ('cancelled', 'キャンセル'),
    ('past_due', '支払い遅延'),
]


class HospitalAdminProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='hospital_profile', verbose_name='ユーザー'
    )
    hospital = models.ForeignKey(
        'hospitals.Hospital', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='admin_profiles', verbose_name='担当病院'
    )
    stripe_customer_id = models.CharField('Stripe顧客ID', max_length=100, blank=True)
    stripe_subscription_id = models.CharField('StripeサブスクリプションID', max_length=100, blank=True)
    subscription_status = models.CharField(
        'サブスクリプション状態', max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES, default='inactive'
    )
    subscription_plan = models.CharField(
        'プラン', max_length=10,
        choices=[('monthly', '月額'), ('yearly', '年額')], blank=True
    )
    subscription_end = models.DateTimeField('掲載期限', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '病院管理者プロフィール'
        verbose_name_plural = '病院管理者プロフィール'

    def __str__(self):
        return f"{self.user.email} ({self.hospital})"

    def is_subscription_active(self):
        from django.utils import timezone
        return (
            self.subscription_status == 'active' and
            (self.subscription_end is None or self.subscription_end > timezone.now())
        )


APPLICATION_STATUS_CHOICES = [
    ('pending', '審査中'),
    ('approved', '承認済み'),
    ('rejected', '却下'),
]


class HospitalAdminApplication(models.Model):
    facility_name = models.CharField('施設名', max_length=200)
    hospital = models.ForeignKey(
        'hospitals.Hospital', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='admin_applications', verbose_name='紐づけ病院'
    )
    contact_name = models.CharField('担当者名', max_length=100)
    email = models.EmailField('メールアドレス')
    phone = models.CharField('電話番号', max_length=20)
    official_url = models.URLField('公式サイトURL', blank=True)
    message = models.TextField('その他備考', blank=True)
    agreed_to_terms = models.BooleanField('利用規約同意', default=False)
    status = models.CharField(
        '審査状態', max_length=10,
        choices=APPLICATION_STATUS_CHOICES, default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField('審査日時', null=True, blank=True)

    class Meta:
        verbose_name = '病院掲載申請'
        verbose_name_plural = '病院掲載申請'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.facility_name}（{self.email}）"


class JobPost(models.Model):
    hospital = models.ForeignKey(
        'hospitals.Hospital', on_delete=models.CASCADE,
        related_name='job_posts', verbose_name='病院・施設'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='job_posts', verbose_name='作成者'
    )
    title = models.CharField('求人タイトル', max_length=200)
    employment_type = models.CharField(
        '雇用形態', max_length=15, choices=EMPLOYMENT_TYPE_CHOICES
    )
    salary_min = models.PositiveIntegerField('年収下限（万円）', null=True, blank=True)
    salary_max = models.PositiveIntegerField('年収上限（万円）', null=True, blank=True)
    description = models.TextField('仕事内容')
    requirements = models.TextField('応募条件', blank=True)
    benefits = models.TextField('福利厚生', blank=True)
    is_active = models.BooleanField('掲載中', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '求人情報'
        verbose_name_plural = '求人情報'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.hospital.name} - {self.title}"

    def get_salary_display(self):
        if self.salary_min and self.salary_max:
            return f"{self.salary_min}〜{self.salary_max}万円"
        if self.salary_min:
            return f"{self.salary_min}万円〜"
        if self.salary_max:
            return f"〜{self.salary_max}万円"
        return '応相談'
