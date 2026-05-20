from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST


from django.contrib.auth import update_session_auth_hash


def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('account_login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@staff_required
def dashboard(request):
    from hospitals.models import FacilityRequest
    from accounts.models import ContactMessage
    from jobs.models import HospitalAdminApplication
    from reviews.models import Objection, Review

    context = {
        'facility_request_count': FacilityRequest.objects.filter(status='pending').count(),
        'contact_unread_count': ContactMessage.objects.filter(is_read=False).count(),
        'job_application_count': HospitalAdminApplication.objects.filter(status='pending').count(),
        'objection_count': Objection.objects.filter(status='pending').count(),
        'review_pending_count': Review.objects.filter(status='pending').count(),
    }
    return render(request, 'panel/dashboard.html', context)


# ── 施設登録申請 ──────────────────────────────────────────

@staff_required
def facility_requests(request):
    from hospitals.models import FacilityRequest
    items = FacilityRequest.objects.select_related('user').order_by('-created_at')
    status_filter = request.GET.get('status', 'pending')
    if status_filter:
        items = items.filter(status=status_filter)
    return render(request, 'panel/facility_requests.html', {
        'items': items,
        'status_filter': status_filter,
    })


@staff_required
@require_POST
def facility_request_action(request, pk):
    from hospitals.models import FacilityRequest, Hospital
    from reviews.models import Review
    req = get_object_or_404(FacilityRequest, pk=pk)
    action = request.POST.get('action')

    if action == 'approve' and req.status in ('pending', 'needs_review'):
        hospital = Hospital.objects.create(
            name=req.facility_name,
            prefecture=req.prefecture,
            address=req.address or req.prefecture,
            facility_type=req.facility_type,
        )
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
        messages.success(request, f'「{req.facility_name}」を承認しました。')

    elif action == 'needs_review':
        req.status = 'needs_review'
        req.save()
        messages.info(request, f'「{req.facility_name}」を要確認にしました。')

    elif action == 'reject':
        req.status = 'rejected'
        req.save()
        messages.warning(request, f'「{req.facility_name}」を却下しました。')

    return redirect('panel_facility_requests')


@staff_required
def facility_request_detail(request, pk):
    from hospitals.models import FacilityRequest
    item = get_object_or_404(FacilityRequest, pk=pk)
    return render(request, 'panel/facility_request_detail.html', {'item': item})


# ── お問い合わせ ──────────────────────────────────────────

@staff_required
def contacts(request):
    from accounts.models import ContactMessage
    items = ContactMessage.objects.order_by('-created_at')
    unread_only = request.GET.get('unread') == '1'
    if unread_only:
        items = items.filter(is_read=False)
    return render(request, 'panel/contacts.html', {
        'items': items,
        'unread_only': unread_only,
    })


@staff_required
@require_POST
def contact_mark_read(request, pk):
    from accounts.models import ContactMessage
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_read = True
    msg.save()
    return redirect('panel_contacts')


# ── 求人掲載申込 ──────────────────────────────────────────

@staff_required
def job_applications(request):
    from jobs.models import HospitalAdminApplication
    items = HospitalAdminApplication.objects.order_by('-created_at')
    status_filter = request.GET.get('status', 'pending')
    if status_filter:
        items = items.filter(status=status_filter)
    return render(request, 'panel/job_applications.html', {
        'items': items,
        'status_filter': status_filter,
    })


@staff_required
@require_POST
def job_application_action(request, pk):
    from jobs.models import HospitalAdminApplication
    app = get_object_or_404(HospitalAdminApplication, pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        app.status = 'approved'
        app.save()
        messages.success(request, f'「{app.facility_name}」の申請を承認しました。')
    elif action == 'reject':
        app.status = 'rejected'
        app.save()
        messages.warning(request, f'「{app.facility_name}」の申請を却下しました。')
    return redirect('panel_job_applications')


# ── 異議申し立て ──────────────────────────────────────────

@staff_required
def objections(request):
    from reviews.models import Objection
    items = Objection.objects.select_related('review__hospital').order_by('-created_at')
    status_filter = request.GET.get('status', 'pending')
    if status_filter:
        items = items.filter(status=status_filter)
    return render(request, 'panel/objections.html', {
        'items': items,
        'status_filter': status_filter,
    })


@staff_required
@require_POST
def objection_action(request, pk):
    from reviews.models import Objection
    obj = get_object_or_404(Objection, pk=pk)
    action = request.POST.get('action')
    if action == 'hide':
        obj.status = 'resolved_hide'
        obj.save()
        obj.review.status = 'rejected'
        obj.review.save()
        messages.success(request, 'レビューを非公開にしました。')
    elif action == 'keep':
        obj.status = 'resolved_keep'
        obj.save()
        obj.review.status = 'approved'
        obj.review.save()
        messages.info(request, 'レビューを公開維持にしました。')
    return redirect('panel_objections')


# ── レビュー審査 ──────────────────────────────────────────

@staff_required
def reviews(request):
    from reviews.models import Review
    items = Review.objects.select_related('hospital', 'user').order_by('-created_at')
    status_filter = request.GET.get('status', 'pending')
    if status_filter:
        items = items.filter(status=status_filter)
    return render(request, 'panel/reviews.html', {
        'items': items,
        'status_filter': status_filter,
    })


@staff_required
def review_detail(request, pk):
    from reviews.models import Review
    item = get_object_or_404(Review, pk=pk)
    return render(request, 'panel/review_detail.html', {'item': item})


@staff_required
@require_POST
def review_action(request, pk):
    from reviews.models import Review
    review = get_object_or_404(Review, pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        review.status = 'approved'
        review.save()
        messages.success(request, 'レビューを承認しました。')
    elif action == 'reject':
        review.status = 'rejected'
        review.save()
        messages.warning(request, 'レビューを却下しました。')
    elif action == 'delete':
        review.delete()
        messages.warning(request, 'レビューを削除しました。')
    return redirect('panel_reviews')


# ── ユーザー管理 ──────────────────────────────────────────

@staff_required
def change_password(request):
    if request.method == 'POST':
        current = request.POST.get('current_password', '')
        new1 = request.POST.get('new_password1', '')
        new2 = request.POST.get('new_password2', '')
        if not request.user.check_password(current):
            messages.error(request, '現在のパスワードが正しくありません。')
        elif new1 != new2:
            messages.error(request, '新しいパスワードが一致しません。')
        elif len(new1) < 8:
            messages.error(request, 'パスワードは8文字以上にしてください。')
        else:
            request.user.set_password(new1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'パスワードを変更しました。')
            return redirect('panel_dashboard')
    return render(request, 'panel/change_password.html')


@staff_required
def users(request):
    from accounts.models import User
    keyword = request.GET.get('keyword', '')
    items = User.objects.order_by('-date_joined')
    if keyword:
        items = items.filter(email__icontains=keyword)
    return render(request, 'panel/users.html', {
        'items': items,
        'keyword': keyword,
    })


@staff_required
@require_POST
def user_action(request, pk):
    from accounts.models import User
    target = get_object_or_404(User, pk=pk)
    action = request.POST.get('action')
    if target.is_staff:
        messages.error(request, 'スタッフアカウントは操作できません。')
        return redirect('panel_users')
    if action == 'deactivate':
        target.is_active = False
        target.save()
        messages.warning(request, f'{target.email} を停止しました。')
    elif action == 'activate':
        target.is_active = True
        target.save()
        messages.success(request, f'{target.email} を有効化しました。')
    return redirect('panel_users')
