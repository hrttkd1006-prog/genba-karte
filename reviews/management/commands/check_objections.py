"""
異議申し立ての返答期限チェック。
期限切れ（72時間以内に返答なし）のレビューを自動非公開にする。
Windowsタスクスケジューラまたはcronで1時間ごとに実行すること。
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from reviews.models import Objection, Review


class Command(BaseCommand):
    help = '返答期限切れの異議申し立てを処理し、対象レビューを非公開にする'

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Objection.objects.filter(
            status='waiting_reply',
            reply_deadline__lt=now,
        ).select_related('review')

        count = 0
        for obj in expired:
            review = obj.review
            if review.status in ('approved', 'objection'):
                review.status = 'rejected'
                review.save(update_fields=['status', 'updated_at'])
            obj.status = 'resolved_hide'
            obj.save(update_fields=['status'])
            count += 1
            self.stdout.write(f'  非公開: レビューID={review.pk}  施設={review.hospital.name}')

        self.stdout.write(
            self.style.SUCCESS(f'完了: {count}件の期限切れ異議申し立てを処理しました ({now.strftime("%Y-%m-%d %H:%M")})')
        )
