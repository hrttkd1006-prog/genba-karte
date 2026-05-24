import stripe
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from django.core.mail import send_mail

from django.db import models
from hospitals.models import Hospital
from .models import JobPost, HospitalAdminProfile, HospitalAdminApplication, EMPLOYMENT_TYPE_CHOICES
from hospitals.models import FACILITY_TYPE_CHOICES
from .forms import JobPostForm, HospitalAdminApplyForm, HospitalRegisterForm
from .decorators import hospital_admin_required

stripe.api_key = settings.STRIPE_SECRET_KEY


def job_list(request):
    jobs = JobPost.objects.filter(is_active=True).select_related('hospital').order_by('-created_at')

    prefecture = request.GET.get('prefecture', '')
    employment_type = request.GET.get('employment_type', '')
    facility_type = request.GET.get('facility_type', '')
    keyword = request.GET.get('keyword', '')

    if prefecture:
        jobs = jobs.filter(hospital__prefecture=prefecture)
    if employment_type:
        jobs = jobs.filter(employment_type=employment_type)
    if facility_type:
        jobs = jobs.filter(hospital__facility_type=facility_type)
    if keyword:
        jobs = jobs.filter(
            models.Q(title__icontains=keyword) |
            models.Q(hospital__name__icontains=keyword) |
            models.Q(description__icontains=keyword)
        )

    from hospitals.models import PREFECTURE_CHOICES
    return render(request, 'jobs/job_list.html', {
        'jobs': jobs,
        'prefecture': prefecture,
        'employment_type': employment_type,
        'facility_type': facility_type,
        'keyword': keyword,
        'prefectures': PREFECTURE_CHOICES,
        'employment_types': EMPLOYMENT_TYPE_CHOICES,
        'facility_types': FACILITY_TYPE_CHOICES,
        'total': jobs.count(),
    })



def for_hospitals_landing(request):
    # すでに病院管理者ならダッシュボードへ
    if request.user.is_authenticated and request.user.is_hospital_admin:
        return redirect('hospital_admin_dashboard')
    steps = [
        {'title': '申し込みフォームに入力', 'desc': '施設名・担当者名・連絡先を入力して送信してください。'},
        {'title': '運営による審査（数営業日以内）', 'desc': '内容を確認後、登録メールアドレスに審査結果をお送りします。'},
        {'title': 'アカウント作成', 'desc': '承認メールの案内に従い、アカウントを作成してください。'},
        {'title': 'プランを契約して掲載開始', 'desc': 'ダッシュボードからプランを選択し、決済完了後すぐに求人を掲載できます。'},
    ]
    return render(request, 'jobs/for_hospitals.html', {'steps': steps})


def hospital_register(request):
    # すでに病院管理者ならダッシュボードへ
    if request.user.is_authenticated and request.user.is_hospital_admin:
        messages.info(request, 'すでに病院管理者として登録されています。')
        return redirect('hospital_admin_dashboard')

    # 未ログインのままページを見ている場合：セッションにnextを保存
    # （メール確認後の自動ログイン時にアダプターがここへ戻す）
    if not request.user.is_authenticated:
        request.session['_next_after_login'] = request.path
        request.session.modified = True

    if request.method == 'POST':
        # 未ログインでの送信はログインへ
        if not request.user.is_authenticated:
            return redirect(f'/account/login/?next={request.path}')
        form = HospitalRegisterForm(request.POST)
        if form.is_valid():
            application = form.save()
            admin_email = getattr(settings, 'ADMIN_NOTIFY_EMAIL', None) or settings.DEFAULT_FROM_EMAIL
            send_mail(
                subject=f'【げんばカルテ】新しい病院掲載申請: {application.facility_name}',
                message=f"""新しい病院掲載申請が届きました。

施設名: {application.facility_name}
担当者: {application.contact_name}
メール: {application.email}
電話: {application.phone}
備考: {application.message}

管理パネルで審査してください:
{settings.SITE_URL}/{getattr(settings, 'PANEL_URL_PREFIX', 'manage-gk2025')}/job-applications/
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=True,
            )
            return render(request, 'jobs/hospital_register_done.html', {
                'facility_name': application.facility_name,
            })
    else:
        form = HospitalRegisterForm()
    return render(request, 'jobs/hospital_register.html', {'form': form})


@hospital_admin_required
def hospital_admin_apply(request):
    """病院管理者として施設との紐付けを申請するフォーム。"""
    # すでに紐付け済みならダッシュボードへ
    try:
        profile = request.user.hospital_profile
        if profile.hospital:
            messages.info(request, f'すでに「{profile.hospital.name}」の管理者として登録されています。')
            return redirect('hospital_admin_dashboard')
    except HospitalAdminProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = HospitalAdminApplyForm(request.POST)
        if form.is_valid():
            hospital = form.cleaned_data.get('hospital')
            new_name = form.cleaned_data.get('hospital_name_new', '').strip()
            contact_name = form.cleaned_data['contact_name']
            contact_email = form.cleaned_data['contact_email']
            message_text = form.cleaned_data.get('message', '')

            hospital_label = hospital.name if hospital else f'（新規依頼）{new_name}'

            from django.core.mail import send_mail
            send_mail(
                subject=f'【げんばカルテ】病院管理者登録申請: {hospital_label}',
                message=f"""新しい病院管理者登録申請が届きました。

申請ユーザー: {request.user.email}
担当施設: {hospital_label}
担当者名: {contact_name}
連絡先: {contact_email}
備考: {message_text}

管理画面で確認して、ユーザーを施設に紐付けてください。
管理URL: {settings.SITE_URL}/admin/jobs/hospitaladminprofile/
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )

            messages.success(request, '申請を受け付けました。運営チームが確認後にご連絡します。')
            return redirect('hospital_admin_dashboard')
    else:
        form = HospitalAdminApplyForm()

    return render(request, 'jobs/apply.html', {'form': form})


@hospital_admin_required
def hospital_admin_dashboard(request):
    try:
        profile = request.user.hospital_profile
    except HospitalAdminProfile.DoesNotExist:
        profile = None

    job_posts = []
    if profile and profile.hospital:
        job_posts = JobPost.objects.filter(hospital=profile.hospital, created_by=request.user)

    return render(request, 'jobs/dashboard.html', {
        'profile': profile,
        'job_posts': job_posts,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'is_active': profile.is_subscription_active() if profile else False,
    })


@hospital_admin_required
def job_post_create(request):
    try:
        profile = request.user.hospital_profile
    except HospitalAdminProfile.DoesNotExist:
        messages.error(request, '病院管理者として登録が必要です。')
        return redirect('hospital_admin_dashboard')

    if not profile.is_subscription_active():
        messages.warning(request, '求人を掲載するには掲載プランへの加入が必要です。')
        return redirect('hospital_admin_dashboard')

    if not profile.hospital:
        messages.error(request, '担当施設が設定されていません。管理者にお問い合わせください。')
        return redirect('hospital_admin_dashboard')

    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.hospital = profile.hospital
            job.created_by = request.user
            job.save()
            messages.success(request, '求人情報を登録しました。')
            return redirect('hospital_admin_dashboard')
    else:
        form = JobPostForm()

    return render(request, 'jobs/job_form.html', {'form': form, 'action': '新規登録'})


@hospital_admin_required
def job_post_edit(request, pk):
    job = get_object_or_404(JobPost, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, '求人情報を更新しました。')
            return redirect('hospital_admin_dashboard')
    else:
        form = JobPostForm(instance=job)
    return render(request, 'jobs/job_form.html', {'form': form, 'action': '編集'})


@hospital_admin_required
def job_post_delete(request, pk):
    job = get_object_or_404(JobPost, pk=pk, created_by=request.user)
    if request.method == 'POST':
        job.delete()
        messages.success(request, '求人情報を削除しました。')
    return redirect('hospital_admin_dashboard')


@hospital_admin_required
def create_checkout_session(request):
    plan = request.POST.get('plan', 'monthly')
    price_id = (
        settings.STRIPE_YEARLY_PRICE_ID if plan == 'yearly'
        else settings.STRIPE_MONTHLY_PRICE_ID
    )
    if not price_id:
        messages.error(request, '決済の設定が完了していません。')
        return redirect('hospital_admin_dashboard')

    try:
        profile, _ = HospitalAdminProfile.objects.get_or_create(user=request.user)
        if not profile.stripe_customer_id:
            customer = stripe.Customer.create(email=request.user.email)
            profile.stripe_customer_id = customer.id
            profile.save()

        session = stripe.checkout.Session.create(
            customer=profile.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=settings.SITE_URL + '/jobs/checkout/success/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=settings.SITE_URL + '/jobs/dashboard/',
            metadata={'user_id': str(request.user.pk), 'plan': plan},
        )
        return redirect(session.url, code=303)
    except stripe.StripeError as e:
        messages.error(request, f'決済処理でエラーが発生しました: {e.user_message}')
        return redirect('hospital_admin_dashboard')


@hospital_admin_required
def checkout_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            profile, _ = HospitalAdminProfile.objects.get_or_create(user=request.user)
            plan = session.metadata['plan'] if session.metadata and 'plan' in session.metadata else 'monthly'
            profile.stripe_subscription_id = str(session.subscription)
            profile.subscription_status = 'active'
            profile.subscription_plan = plan
            profile.save()
            messages.success(request, '掲載プランへの加入が完了しました。求人情報を登録できます。')
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'checkout_success error: {e}')
            messages.error(request, '処理中にエラーが発生しました。管理者にお問い合わせください。')
    return redirect('hospital_admin_dashboard')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'customer.subscription.deleted':
        sub = event['data']['object']
        HospitalAdminProfile.objects.filter(
            stripe_subscription_id=sub['id']
        ).update(subscription_status='cancelled')

    elif event['type'] == 'invoice.payment_failed':
        sub_id = event['data']['object'].get('subscription')
        if sub_id:
            HospitalAdminProfile.objects.filter(
                stripe_subscription_id=sub_id
            ).update(subscription_status='past_due')

    elif event['type'] == 'invoice.payment_succeeded':
        sub_id = event['data']['object'].get('subscription')
        if sub_id:
            HospitalAdminProfile.objects.filter(
                stripe_subscription_id=sub_id
            ).update(subscription_status='active')

    return HttpResponse(status=200)
