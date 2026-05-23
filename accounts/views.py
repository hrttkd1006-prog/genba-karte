from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProfileForm


def top(request):
    from reviews.models import Review
    from hospitals.models import PREFECTURE_CHOICES
    recent_reviews = Review.objects.filter(status='approved').select_related('hospital')[:5]
    return render(request, 'pages/top.html', {
        'recent_reviews': recent_reviews,
        'prefectures': PREFECTURE_CHOICES,
    })


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'プロフィールを更新しました。')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    from reviews.models import Review
    user_reviews = Review.objects.filter(user=request.user).select_related('hospital').order_by('-created_at')
    return render(request, 'accounts/profile.html', {'form': form, 'user_reviews': user_reviews})


def terms(request):
    return render(request, 'pages/terms.html')


def privacy(request):
    return render(request, 'pages/privacy.html')


def tokusho(request):
    return render(request, 'pages/tokusho.html')


def about(request):
    return render(request, 'pages/about.html')


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def contact(request):
    if request.method == 'POST':
        from .models import ContactMessage
        from django.core.mail import send_mail
        from django.conf import settings
        from django.utils import timezone
        import datetime

        # ハニーポット（ボット対策）
        if request.POST.get('website', ''):
            return render(request, 'pages/contact.html', {'sent': True})

        # IPレートリミット（1時間に5件まで）
        ip = _get_client_ip(request)
        recent_count = ContactMessage.objects.filter(
            ip_address=ip,
            created_at__gte=timezone.now() - datetime.timedelta(hours=1)
        ).count() if ip else 0
        if recent_count >= 5:
            messages.error(request, '送信回数の上限に達しました。しばらく時間をおいてからお試しください。')
            return render(request, 'pages/contact.html')

        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        category = request.POST.get('category', '')
        message = request.POST.get('message', '')
        if email and message:
            ContactMessage.objects.create(
                name=name,
                email=email,
                category=category,
                message=message,
                ip_address=ip,
            )
            admin_email = getattr(settings, 'ADMIN_NOTIFY_EMAIL', None) or settings.DEFAULT_FROM_EMAIL
            send_mail(
                subject=f'【げんばカルテ】お問い合わせが届きました',
                message=f"お名前: {name}\nメール: {email}\n種別: {category}\n\n内容:\n{message}\n\n管理画面: {settings.SITE_URL}/{getattr(settings, 'PANEL_URL_PREFIX', 'manage-gk2025')}/contacts/",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=True,
            )
            return render(request, 'pages/contact.html', {'sent': True})
    return render(request, 'pages/contact.html')
