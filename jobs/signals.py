from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='accounts.User')
def grant_hospital_admin_on_signup(sender, instance, created, **kwargs):
    """承認済み申請があるメールでサインアップしたら自動で病院管理者フラグを付与"""
    if not created:
        return
    if instance.is_hospital_admin:
        return

    from jobs.models import HospitalAdminApplication, HospitalAdminProfile
    app = HospitalAdminApplication.objects.filter(email=instance.email, status='approved').first()
    if not app:
        return

    instance.is_hospital_admin = True
    instance.save(update_fields=['is_hospital_admin'])
    HospitalAdminProfile.objects.get_or_create(user=instance)
    _ = app  # 申請は参照のみ（複数施設対応のため削除しない）
