from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import Hospital, FacilityRequest


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'prefecture', 'facility_type', 'beds', 'technician_count', 'created_at']
    list_filter = ['prefecture', 'facility_type']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['prefecture', 'name']


@admin.register(FacilityRequest)
class FacilityRequestAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'prefecture', 'facility_type', 'user', 'status', 'created_at']
    list_filter = ['status', 'prefecture', 'facility_type']
    search_fields = ['facility_name', 'address']
    readonly_fields = ['user', 'facility_name', 'prefecture', 'address', 'facility_type',
                       'overall_rating', 'annual_salary', 'overtime_hours', 'employment_type',
                       'has_oncall', 'has_night_duty', 'has_night_shift',
                       'good_points', 'concerns', 'suitable_for', 'joining_gap', 'created_at']
    fields = ['status', 'admin_note',
              'facility_name', 'prefecture', 'address', 'facility_type', 'user', 'created_at',
              'overall_rating', 'annual_salary', 'overtime_hours', 'employment_type',
              'has_oncall', 'has_night_duty', 'has_night_shift',
              'good_points', 'concerns', 'suitable_for', 'joining_gap']
    actions = ['approve_requests', 'needs_review_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        from reviews.models import Review
        approved = 0
        for req in queryset.filter(status='pending') | queryset.filter(status='needs_review'):
            # 施設を作成
            hospital = Hospital.objects.create(
                name=req.facility_name,
                prefecture=req.prefecture,
                address=req.address or req.prefecture,
                facility_type=req.facility_type,
            )
            # レビューがあれば作成
            if req.overall_rating and req.user:
                Review.objects.create(
                    hospital=hospital,
                    user=req.user,
                    overall_rating=req.overall_rating,
                    salary_rating=req.salary_rating,
                    relationship_rating=req.relationship_rating,
                    education_rating=req.education_rating,
                    equipment_rating=req.equipment_rating,
                    annual_salary=req.annual_salary,
                    overtime_hours=req.overtime_hours,
                    paid_leave_rate=req.paid_leave_rate,
                    technician_count=req.technician_count,
                    employment_type=req.employment_type or '',
                    education_system=req.education_system or '',
                    equipment_age=req.equipment_age or '',
                    has_oncall=req.has_oncall,
                    has_night_duty=req.has_night_duty,
                    has_night_shift=req.has_night_shift,
                    has_blood_sampling=req.has_blood_sampling,
                    work_style=req.work_style or '',
                    oncall_night_frequency=req.oncall_night_frequency or '',
                    male_ratio=req.male_ratio,
                    average_age=req.average_age,
                    research_opportunity=req.research_opportunity or '',
                    certification_support=req.certification_support or '',
                    good_points=req.good_points or '',
                    concerns=req.concerns or '',
                    suitable_for=req.suitable_for or '',
                    joining_gap=req.joining_gap or '',
                    agreed_to_terms=True,
                    status='approved',
                )
            req.status = 'approved'
            req.save()
            # 申請者にメール通知
            if req.user:
                send_mail(
                    subject='【げんばカルテ】施設登録申請が承認されました',
                    message=f"""申請いただいた「{req.facility_name}」が登録されました。

レビューも公開されました。ありがとうございます。

げんばカルテ
{settings.SITE_URL}
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[req.user.email],
                    fail_silently=True,
                )
            approved += 1
        self.message_user(request, f'{approved}件を承認し施設を登録しました。')
    approve_requests.short_description = '承認して施設を登録する'

    def needs_review_requests(self, request, queryset):
        for req in queryset:
            req.status = 'needs_review'
            req.save()
            if req.user and req.admin_note:
                send_mail(
                    subject='【げんばカルテ】施設登録申請について確認事項があります',
                    message=f"""申請いただいた「{req.facility_name}」について確認事項があります。

{req.admin_note}

このメールに返信いただくか、お問い合わせページよりご連絡ください。
{settings.SITE_URL}/contact/
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[req.user.email],
                    fail_silently=True,
                )
        self.message_user(request, f'{queryset.count()}件を要確認にしました。')
    needs_review_requests.short_description = '要確認にする（admin_noteを送信）'

    def reject_requests(self, request, queryset):
        for req in queryset:
            req.status = 'rejected'
            req.save()
            if req.user:
                send_mail(
                    subject='【げんばカルテ】施設登録申請について',
                    message=f"""申請いただいた「{req.facility_name}」は今回登録できませんでした。

ご不明な点はお問い合わせページよりご連絡ください。
{settings.SITE_URL}/contact/
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[req.user.email],
                    fail_silently=True,
                )
        self.message_user(request, f'{queryset.count()}件を却下しました。')
    reject_requests.short_description = '却下する'
