from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import datetime

from hospitals.models import Hospital
from .models import Review, Objection, ReviewHelpful
from .forms import ReviewForm
from .ai_moderation import moderate_review, build_review_text


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
def review_create(request, hospital_pk):
    hospital = get_object_or_404(Hospital, pk=hospital_pk)

    if Review.objects.filter(hospital=hospital, user=request.user).exists():
        messages.warning(request, 'この施設にはすでにレビューを投稿済みです。')
        return redirect('hospital_detail', hospital.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.hospital = hospital
            review.user = request.user
            review.ip_address = _get_client_ip(request)

            ip = review.ip_address
            recent_count = Review.objects.filter(
                ip_address=ip,
                created_at__gte=timezone.now() - datetime.timedelta(minutes=10)
            ).count()
            if recent_count >= 3:
                review.status = 'rejected'
                review.ai_judgment = 'black'
                review.ai_reason = '同一IPからの短時間大量投稿のため自動非公開'
                review.save()
                messages.error(request, '投稿が制限されています。しばらく時間をおいてからお試しください。')
                return redirect('hospital_detail', hospital.pk)

            review_text = build_review_text(review)
            ai_result = moderate_review(review_text, ip)
            review.ai_judgment = ai_result['judgment']
            review.ai_reason = ai_result['reason']

            if ai_result['judgment'] == 'black':
                review.status = 'rejected'
                review.reject_reason = ai_result['reason']
            elif ai_result['judgment'] == 'white':
                review.status = 'approved'
            else:
                review.status = 'pending'

            review.save()

            # AIグレー → 管理者にメールで確認を依頼
            if review.status == 'pending':
                admin_email = getattr(settings, 'ADMIN_NOTIFY_EMAIL', None) or settings.DEFAULT_FROM_EMAIL
                send_mail(
                    subject=f'【げんばカルテ】要確認のレビューがあります（{hospital.name}）',
                    message=f"""AIが要確認と判定したレビューがあります。

■ 施設名: {hospital.name}
■ 投稿者: {review.user.email if review.user else '不明'}
■ AI判定理由:
{ai_result['reason']}

管理画面で内容を確認してください:
{settings.SITE_URL}/{getattr(settings, 'PANEL_URL_PREFIX', 'manage-gk2025')}/reviews/{review.pk}/
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=True,
                )

            if review.status == 'approved':
                messages.success(request, 'レビューを投稿しました。ご協力ありがとうございます！')
            elif review.status == 'pending':
                messages.info(request, 'レビューを受け付けました。内容確認後に公開されます（通常数日以内）。')
            else:
                messages.warning(request, '投稿内容の審査により、今回は掲載できませんでした。')

            return redirect('hospital_detail', hospital.pk)
    else:
        form = ReviewForm()

    return render(request, 'reviews/create.html', {
        'form': form,
        'hospital': hospital,
    })


@login_required
def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)
    if request.method == 'POST':
        hospital_pk = review.hospital_id
        review.delete()
        messages.success(request, 'レビューを削除しました。')
        return redirect('profile')
    return render(request, 'reviews/delete_confirm.html', {'review': review})


@login_required
def toggle_helpful(request, pk):
    review = get_object_or_404(Review, pk=pk, status='approved')
    helpful, created = ReviewHelpful.objects.get_or_create(review=review, user=request.user)
    if not created:
        helpful.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))


def recent_reviews(request):
    reviews = Review.objects.filter(status='approved').select_related('hospital', 'user').order_by('-created_at')[:30]
    return render(request, 'reviews/recent.html', {'reviews': reviews})


@login_required
def objection_create(request, review_id):
    review = get_object_or_404(Review, pk=review_id, status='approved')

    if request.method == 'POST':
        hospital_name = request.POST.get('hospital_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        reason = request.POST.get('reason', '').strip()

        if hospital_name and contact_email and reason:
            obj = Objection.objects.create(
                review=review,
                hospital_name=hospital_name,
                contact_email=contact_email,
                reason=reason,
                status='waiting_reply',
            )
            obj.set_reply_deadline()

            review.status = 'objection'
            review.save()

            # 投稿者へ確認メール
            if review.user and review.user.email:
                deadline_str = obj.reply_deadline.strftime('%Y年%m月%d日 %H:%M')
                send_mail(
                    subject='【げんばカルテ】投稿内容についてご確認ください',
                    message=f"""
あなたが投稿したレビューについて、施設側から異議申し立てがありました。

■ 対象施設: {review.hospital.name}

■ 申し立て内容:
{reason}

投稿内容が事実であることをご確認いただける場合は、{deadline_str} までに
下記URLからご返答ください。

{settings.SITE_URL}/reviews/objection-reply/{obj.pk}/

期限までにご返答がない場合、投稿は自動的に非公開となります。

げんばカルテ 運営チーム
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[review.user.email],
                    fail_silently=True,
                )

            # 管理者へ通知
            admin_email = getattr(settings, 'ADMIN_NOTIFY_EMAIL', None) or settings.DEFAULT_FROM_EMAIL
            send_mail(
                subject=f'【げんばカルテ】異議申し立てが届きました（{review.hospital.name}）',
                message=f"施設名: {hospital_name}\n連絡先: {contact_email}\n\n申立理由:\n{reason}\n\n管理画面: {settings.SITE_URL}/{getattr(settings, 'PANEL_URL_PREFIX', 'manage-gk2025')}/objections/",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=True,
            )

            messages.success(request, '異議申し立てを受け付けました。投稿者へ確認メールを送信しました。')
            return redirect('hospital_detail', review.hospital.pk)
        else:
            messages.error(request, '必須項目を入力してください。')

    return render(request, 'reviews/objection.html', {'review': review})


@login_required
def objection_reply(request, objection_id):
    obj = get_object_or_404(Objection, pk=objection_id, status='waiting_reply')
    review = obj.review

    if timezone.now() > obj.reply_deadline:
        review.status = 'rejected'
        review.save()
        obj.status = 'resolved_hide'
        obj.save()
        return render(request, 'reviews/objection_expired.html')

    if request.method == 'POST':
        reply_text = request.POST.get('reply', '').strip()
        obj.status = 'pending'
        obj.save()
        send_mail(
            subject=f'【げんばカルテ】異議申し立て：投稿者から返答があります（ID:{obj.pk}）',
            message=f"異議申し立てID: {obj.pk}\n施設: {review.hospital.name}\n投稿者の返答:\n{reply_text}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )
        return render(request, 'reviews/objection_replied.html')

    return render(request, 'reviews/objection_reply.html', {'objection': obj})
