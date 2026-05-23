from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField('メールアドレス', unique=True)
    workplace = models.CharField('勤務先・学校名', max_length=200, blank=True)
    is_hospital_admin = models.BooleanField('病院管理者', default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'

    def __str__(self):
        return self.email


CONTACT_CATEGORY_CHOICES = [
    ('general', '一般的なお問い合わせ'),
    ('review', 'レビューについて'),
    ('facility', '施設情報について'),
    ('account', 'アカウントについて'),
    ('other', 'その他'),
]


class ContactMessage(models.Model):
    name = models.CharField('お名前', max_length=100)
    email = models.EmailField('メールアドレス')
    category = models.CharField('種別', max_length=20, choices=CONTACT_CATEGORY_CHOICES, blank=True)
    message = models.TextField('内容')
    is_read = models.BooleanField('確認済み', default=False)
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'お問い合わせ'
        verbose_name_plural = 'お問い合わせ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name}（{self.email}）- {self.created_at.strftime('%Y/%m/%d')}"
