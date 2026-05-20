from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = '月次レポートを管理者メールに送信する'

    def handle(self, *args, **options):
        from accounts.models import User, ContactMessage
        from reviews.models import Review
        from hospitals.models import Hospital, FacilityRequest

        now = timezone.now()
        month_ago = now - datetime.timedelta(days=30)

        new_users = User.objects.filter(date_joined__gte=month_ago).count()
        total_users = User.objects.count()

        new_reviews = Review.objects.filter(created_at__gte=month_ago).count()
        total_reviews = Review.objects.filter(status='approved').count()
        pending_reviews = Review.objects.filter(status='pending').count()

        new_hospitals = Hospital.objects.filter(created_at__gte=month_ago).count()
        total_hospitals = Hospital.objects.count()

        pending_requests = FacilityRequest.objects.filter(status='pending').count()
        unread_contacts = ContactMessage.objects.filter(is_read=False).count()

        body = f"""
【げんばカルテ 月次レポート】
集計期間: {month_ago.strftime('%Y/%m/%d')} 〜 {now.strftime('%Y/%m/%d')}

■ ユーザー
  新規登録: {new_users}名
  累計: {total_users}名

■ レビュー
  新規投稿: {new_reviews}件
  公開中累計: {total_reviews}件
  審査待ち: {pending_reviews}件

■ 施設
  新規登録: {new_hospitals}件
  累計: {total_hospitals}件

■ 要対応
  施設登録申請（審査待ち）: {pending_requests}件
  未読お問い合わせ: {unread_contacts}件

管理画面: {settings.SITE_URL}/{getattr(settings, 'PANEL_URL_PREFIX', 'manage-gk2025')}/
"""

        admin_email = getattr(settings, 'ADMIN_NOTIFY_EMAIL', None) or settings.DEFAULT_FROM_EMAIL
        send_mail(
            subject=f'【げんばカルテ】月次レポート {now.strftime("%Y年%m月")}',
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
        )
        self.stdout.write(self.style.SUCCESS(f'月次レポートを {admin_email} に送信しました'))
