from django.contrib import admin, messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from .models import JobPost, HospitalAdminProfile, HospitalAdminApplication


def approve_applications(modeladmin, request, queryset):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    approved_count = 0
    for app in queryset.filter(status='pending'):
        # ユーザー取得または作成
        user, created = User.objects.get_or_create(
            email=app.email,
            defaults={'is_hospital_admin': True},
        )
        if not created:
            user.is_hospital_admin = True
            user.save(update_fields=['is_hospital_admin'])

        # プロフィール作成
        HospitalAdminProfile.objects.get_or_create(user=user)

        # 申請ステータス更新
        app.status = 'approved'
        app.reviewed_at = timezone.now()
        app.save()

        # 承認メール送信
        if created:
            subject = '【げんばカルテ】掲載申請が承認されました'
            body = f"""{app.contact_name} 様

この度はげんばカルテへの掲載申請をいただきありがとうございます。
審査の結果、{app.facility_name} 様の掲載申請を承認いたしました。

以下のURLからアカウントを作成してください（申請時のメールアドレスでご登録ください）。

{settings.SITE_URL}/accounts/signup/

アカウント作成後、ダッシュボードからプランをご契約いただくと
求人情報を掲載できるようになります。

ご不明な点がございましたらお気軽にお問い合わせください。

げんばカルテ 運営チーム
"""
        else:
            subject = '【げんばカルテ】掲載申請が承認されました'
            body = f"""{app.contact_name} 様

この度はげんばカルテへの掲載申請をいただきありがとうございます。
審査の結果、{app.facility_name} 様の掲載申請を承認いたしました。

以下のURLからログインしてダッシュボードをご確認ください。

{settings.SITE_URL}/accounts/login/

プランをご契約いただくと求人情報を掲載できるようになります。

ご不明な点がございましたらお気軽にお問い合わせください。

げんばカルテ 運営チーム
"""
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[app.email],
            fail_silently=True,
        )
        approved_count += 1

    messages.success(request, f'{approved_count}件の申請を承認し、メールを送信しました。')


approve_applications.short_description = '選択した申請を承認してメールを送信'


def reject_applications(modeladmin, request, queryset):
    from django.conf import settings
    count = queryset.filter(status='pending').update(
        status='rejected',
        reviewed_at=timezone.now(),
    )
    messages.success(request, f'{count}件の申請を却下しました。')


reject_applications.short_description = '選択した申請を却下'


@admin.register(HospitalAdminApplication)
class HospitalAdminApplicationAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'contact_name', 'email', 'phone', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['facility_name', 'email', 'contact_name']
    readonly_fields = ['created_at', 'reviewed_at']
    actions = [approve_applications, reject_applications]
    ordering = ['-created_at']


@admin.register(HospitalAdminProfile)
class HospitalAdminProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'hospital', 'subscription_status', 'subscription_plan', 'subscription_end']
    list_filter = ['subscription_status', 'subscription_plan']
    search_fields = ['user__email', 'hospital__name']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id', 'created_at']


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'hospital', 'employment_type', 'get_salary_display', 'is_active', 'created_at']
    list_filter = ['employment_type', 'is_active']
    search_fields = ['title', 'hospital__name']
