from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST


from django.contrib.auth import update_session_auth_hash


def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('two_factor:login')
        if not request.user.is_verified():
            from two_factor.views import LoginView
            return redirect('two_factor:login')
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
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
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
        if req.user:
            send_mail(
                subject='【げんばカルテ】施設登録申請が承認されました',
                message=f"""この度は「げんばカルテ」への施設登録申請をいただきありがとうございます。
審査の結果、「{req.facility_name}」の登録が承認され、口コミが公開されました。

施設ページはこちらからご確認いただけます。
{django_settings.SITE_URL}/hospitals/{hospital.pk}/

今後ともげんばカルテをよろしくお願いいたします。

げんばカルテ 運営事務局
""",
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[req.user.email],
                fail_silently=True,
            )
        messages.success(request, f'「{req.facility_name}」を承認しました。')

    elif action == 'needs_review':
        req.status = 'needs_review'
        req.save()
        messages.info(request, f'「{req.facility_name}」を要確認にしました。')

    elif action == 'reject':
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        req.status = 'rejected'
        req.save()
        if req.user:
            send_mail(
                subject='【げんばカルテ】施設登録申請について',
                message=f"""この度は「げんばカルテ」への施設登録申請をいただきありがとうございます。
審査の結果、「{req.facility_name}」の登録申請については、今回は見送りとさせていただきました。

ご不明な点はお問い合わせフォームよりご連絡ください。
{django_settings.SITE_URL}/contact/

げんばカルテ 運営事務局
""",
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[req.user.email],
                fail_silently=True,
            )
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
    from hospitals.models import Hospital
    items = HospitalAdminApplication.objects.select_related('hospital').order_by('-created_at')
    status_filter = request.GET.get('status', 'pending')
    if status_filter:
        items = items.filter(status=status_filter)
    hospitals = Hospital.objects.order_by('prefecture', 'name')
    return render(request, 'panel/job_applications.html', {
        'items': items,
        'status_filter': status_filter,
        'hospitals': hospitals,
    })


@staff_required
@require_POST
def job_application_action(request, pk):
    from jobs.models import HospitalAdminApplication, HospitalAdminProfile
    from hospitals.models import Hospital
    from accounts.models import User
    app = get_object_or_404(HospitalAdminApplication, pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        app.status = 'approved'
        app.save()

        from django.core.mail import send_mail
        from django.conf import settings as django_settings

        # 申請時にログイン必須のため、アカウントは必ず存在する
        try:
            user = User.objects.get(email=app.email)
            user.is_hospital_admin = True
            user.save(update_fields=['is_hospital_admin'])

            # 手動選択した病院を優先、なければ申請時選択、なければ施設名で部分一致
            hospital_id = request.POST.get('hospital_id')
            if hospital_id:
                hospital = Hospital.objects.filter(pk=hospital_id).first()
            elif app.hospital:
                hospital = app.hospital
            else:
                hospital = Hospital.objects.filter(name__icontains=app.facility_name).first()

            # HospitalAdminProfile を作成または更新
            profile, _ = HospitalAdminProfile.objects.get_or_create(user=user)
            if hospital and not profile.hospital:
                profile.hospital = hospital
                profile.save(update_fields=['hospital'])

            # 承認メール送信
            send_mail(
                subject='【げんばカルテ】掲載申請が承認されました',
                message=f"""{app.contact_name} 様

この度は「げんばカルテ」への掲載申請をいただきありがとうございます。
審査の結果、「{app.facility_name}」の掲載申請が承認されました。

以下のURLからログインし、掲載プランをお選びください。
ダッシュボード: {django_settings.SITE_URL}/jobs/dashboard/

プランは月額1,000円（税別）または年額10,000円（税別）です。
プランへの加入が完了すると、求人情報の掲載が開始されます。

ご不明な点はお問い合わせフォームよりご連絡ください。
{django_settings.SITE_URL}/contact/

げんばカルテ 運営事務局
""",
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[app.email],
                fail_silently=True,
            )
            messages.success(request, f'「{app.facility_name}」を承認しました。{app.email} に病院管理者権限を付与し、承認メールを送信しました。')
        except User.DoesNotExist:
            messages.warning(request, f'「{app.facility_name}」を承認しましたが、{app.email} のアカウントが見つかりません。該当ユーザーに直接ご連絡ください。')

    elif action == 'relink':
        hospital_id = request.POST.get('hospital_id')
        if hospital_id:
            hospital = Hospital.objects.filter(pk=hospital_id).first()
            if hospital:
                app.hospital = hospital
                app.save(update_fields=['hospital'])
                try:
                    from accounts.models import User
                    user = User.objects.get(email=app.email)
                    profile, _ = HospitalAdminProfile.objects.get_or_create(user=user)
                    profile.hospital = hospital
                    profile.save(update_fields=['hospital'])
                    messages.success(request, f'「{app.facility_name}」の担当施設を「{hospital.name}」に更新しました。')
                except User.DoesNotExist:
                    messages.warning(request, f'申請の病院は更新しましたが、ユーザーが見つかりません。')
            else:
                messages.error(request, '病院が見つかりませんでした。')
        else:
            messages.error(request, '病院を選択してください。')

    elif action == 'reject':
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        app.status = 'rejected'
        app.save()
        send_mail(
            subject='【げんばカルテ】掲載申請について',
            message=f"""{app.contact_name} 様

この度は「げんばカルテ」への掲載申請をいただきありがとうございます。
審査の結果、今回は掲載申請を見送りとさせていただきました。

ご不明な点はお問い合わせフォームよりご連絡ください。
{django_settings.SITE_URL}/contact/

げんばカルテ 運営事務局
""",
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[app.email],
            fail_silently=True,
        )
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
    from django.core.mail import send_mail
    from django.conf import settings as django_settings
    if action == 'approve':
        review.status = 'approved'
        review.save()
        if review.user and review.user.email:
            send_mail(
                subject='【げんばカルテ】レビューが公開されました',
                message=f"""レビューが審査を通過し、公開されました。

■ 施設名: {review.hospital.name}

ご協力いただきありがとうございます。
施設ページはこちらからご確認いただけます。
{django_settings.SITE_URL}/hospitals/{review.hospital.pk}/

げんばカルテ 運営チーム
""",
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[review.user.email],
                fail_silently=True,
            )
        messages.success(request, 'レビューを承認しました。')
    elif action == 'reject':
        review.status = 'rejected'
        review.reject_reason = request.POST.get('reject_reason', '').strip()
        review.save()
        if review.user and review.user.email:
            send_mail(
                subject='【げんばカルテ】レビューについてのお知らせ',
                message=f"""投稿いただいたレビューについて、審査の結果、今回は掲載を見送らせていただきました。

■ 施設名: {review.hospital.name}
{f"■ 理由: {review.reject_reason}" if review.reject_reason else ""}

ご不明な点はお問い合わせフォームよりご連絡ください。
{django_settings.SITE_URL}/contact/

げんばカルテ 運営チーム
""",
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[review.user.email],
                fail_silently=True,
            )
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
    elif action == 'delete':
        email = target.email
        target.delete()
        messages.warning(request, f'{email} を削除しました。')
    return redirect('panel_users')


# ── 求人管理 ──────────────────────────────────────────

@staff_required
def job_posts_panel(request):
    from jobs.models import JobPost
    items = JobPost.objects.select_related('hospital', 'created_by').order_by('-created_at')
    keyword = request.GET.get('keyword', '')
    if keyword:
        items = items.filter(hospital__name__icontains=keyword)
    return render(request, 'panel/job_posts.html', {
        'items': items,
        'keyword': keyword,
    })


@staff_required
@require_POST
def job_post_action(request, pk):
    from jobs.models import JobPost
    job = get_object_or_404(JobPost, pk=pk)
    action = request.POST.get('action')
    if action == 'delete':
        title = job.title
        job.delete()
        messages.warning(request, f'「{title}」を削除しました。')
    elif action == 'deactivate':
        job.is_active = False
        job.save()
        messages.warning(request, f'「{job.title}」を非公開にしました。')
    elif action == 'activate':
        job.is_active = True
        job.save()
        messages.success(request, f'「{job.title}」を公開しました。')
    return redirect('panel_job_posts')


# ── サーバーログ ──────────────────────────────────────────

@staff_required
def server_logs(request):
    from panel.models import ServerLog
    logs = ServerLog.objects.order_by('-date')[:30]
    latest = logs[0] if logs else None
    return render(request, 'panel/server_logs.html', {
        'logs': logs,
        'latest': latest,
    })


# ── 記事管理 ──────────────────────────────────────────

@staff_required
def article_list_panel(request):
    from articles.models import Article
    items = Article.objects.select_related('author').order_by('-created_at')
    return render(request, 'panel/article_list.html', {'items': items})


@staff_required
def article_create(request):
    from articles.models import Article, ARTICLE_CATEGORY_CHOICES
    from django.utils import timezone
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        category = request.POST.get('category', 'tips')
        is_published = request.POST.get('is_published') == 'on'
        thumbnail = request.FILES.get('thumbnail')
        if title and body:
            article = Article(
                title=title,
                body=body,
                category=category,
                is_published=is_published,
                author=request.user,
            )
            if thumbnail:
                article.thumbnail = thumbnail
            if is_published:
                article.published_at = timezone.now()
            article.save()
            messages.success(request, '記事を作成しました。')
            return redirect('panel_article_list')
        else:
            messages.error(request, 'タイトルと本文は必須です。')
    from articles.models import ARTICLE_CATEGORY_CHOICES
    return render(request, 'panel/article_form.html', {
        'categories': ARTICLE_CATEGORY_CHOICES,
        'action': 'create',
    })


@staff_required
def article_edit(request, pk):
    from articles.models import Article, ARTICLE_CATEGORY_CHOICES
    from django.utils import timezone
    article = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        article.title = request.POST.get('title', '').strip()
        article.body = request.POST.get('body', '').strip()
        article.category = request.POST.get('category', 'tips')
        was_published = article.is_published
        article.is_published = request.POST.get('is_published') == 'on'
        if request.FILES.get('thumbnail'):
            article.thumbnail = request.FILES['thumbnail']
        if article.is_published and not was_published:
            article.published_at = timezone.now()
        if article.title and article.body:
            article.save()
            messages.success(request, '記事を更新しました。')
            return redirect('panel_article_list')
        else:
            messages.error(request, 'タイトルと本文は必須です。')
    return render(request, 'panel/article_form.html', {
        'article': article,
        'categories': ARTICLE_CATEGORY_CHOICES,
        'action': 'edit',
    })


@staff_required
@require_POST
def article_delete(request, pk):
    from articles.models import Article
    article = get_object_or_404(Article, pk=pk)
    article.delete()
    messages.warning(request, '記事を削除しました。')
    return redirect('panel_article_list')
