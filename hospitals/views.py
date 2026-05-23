from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from .models import Hospital, Favorite, PREFECTURE_CHOICES


def hospital_list(request):
    hospitals = Hospital.objects.all()
    prefecture = request.GET.get('prefecture', '')
    keyword = request.GET.get('keyword', '')
    facility_type = request.GET.get('facility_type', '')
    sort = request.GET.get('sort', 'reviews')

    if prefecture:
        hospitals = hospitals.filter(prefecture=prefecture)
    if keyword:
        hospitals = hospitals.filter(Q(name__icontains=keyword) | Q(address__icontains=keyword))
    if facility_type:
        hospitals = hospitals.filter(facility_type=facility_type)

    hospitals = hospitals.annotate(
        review_count=Count('reviews', filter=Q(reviews__status='approved')),
        avg_rating=Avg('reviews__overall_rating', filter=Q(reviews__status='approved')),
    )

    if sort == 'rating':
        hospitals = hospitals.order_by('-avg_rating', '-review_count', 'name')
    elif sort == 'name':
        hospitals = hospitals.order_by('prefecture', 'name')
    else:
        hospitals = hospitals.order_by('-review_count', 'name')

    paginator = Paginator(hospitals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hospitals/list.html', {
        'hospitals': page_obj,
        'page_obj': page_obj,
        'prefectures': PREFECTURE_CHOICES,
        'selected_prefecture': prefecture,
        'keyword': keyword,
        'facility_type': facility_type,
        'sort': sort,
    })


@login_required
def facility_request_create(request):
    from .forms import FacilityRequestForm

    if request.method == 'POST':
        form = FacilityRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.user = request.user
            req.save()
            from django.contrib import messages
            messages.success(request, '申請を送信しました。審査後にレビューが公開されます。')
            return redirect('hospital_list')
    else:
        form = FacilityRequestForm()
    return render(request, 'hospitals/facility_request.html', {'form': form})


@login_required
def toggle_favorite(request, pk):
    hospital = get_object_or_404(Hospital, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, hospital=hospital)
    if not created:
        fav.delete()
    return redirect(request.META.get('HTTP_REFERER', 'hospital_detail'))


@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('hospital').order_by('-created_at')
    return render(request, 'hospitals/favorites.html', {'favorites': favorites})


def hospital_autocomplete(request):
    from django.http import JsonResponse
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse([], safe=False)
    results = Hospital.objects.filter(
        Q(name__icontains=q) | Q(address__icontains=q)
    ).values('id', 'name', 'prefecture')[:10]
    return JsonResponse(list(results), safe=False)


def hospital_map(request):
    hospitals_with_coords = Hospital.objects.filter(
        lat__isnull=False, lng__isnull=False
    ).annotate(
        review_count=Count('reviews', filter=Q(reviews__status='approved')),
        avg_rating=Avg('reviews__overall_rating', filter=Q(reviews__status='approved')),
    )

    # 座標なし施設は都道府県集計で表示
    prefecture_data = Hospital.objects.filter(lat__isnull=True).values('prefecture').annotate(
        count=Count('id'),
    )
    no_coord_prefectures = {row['prefecture']: row['count'] for row in prefecture_data}

    total = Hospital.objects.count()
    geocoded = hospitals_with_coords.count()

    return render(request, 'hospitals/map.html', {
        'hospitals': hospitals_with_coords,
        'no_coord_prefectures': no_coord_prefectures,
        'geocoded': geocoded,
        'total': total,
    })


def hospital_detail(request, pk):
    hospital = get_object_or_404(Hospital, pk=pk)
    from reviews.models import Review
    from jobs.models import JobPost, HospitalAdminProfile

    sort = request.GET.get('sort', 'newest')
    reviews = Review.objects.filter(hospital=hospital, status='approved').select_related('user')
    if sort == 'rating_high':
        reviews = reviews.order_by('-overall_rating', '-created_at')
    elif sort == 'rating_low':
        reviews = reviews.order_by('overall_rating', '-created_at')
    else:
        reviews = reviews.order_by('-created_at')

    avg_rating = reviews.aggregate(avg=Avg('overall_rating'))['avg']
    avg_salary = reviews.aggregate(avg=Avg('annual_salary'))['avg']
    avg_overtime = reviews.aggregate(avg=Avg('overtime_hours'))['avg']

    # 求人（掲載中の病院管理者がいる場合のみ）
    job_posts = []
    admin_profiles = HospitalAdminProfile.objects.filter(hospital=hospital)
    for profile in admin_profiles:
        if profile.is_subscription_active():
            job_posts = JobPost.objects.filter(hospital=hospital, is_active=True)
            break

    is_favorite = (
        request.user.is_authenticated and
        Favorite.objects.filter(user=request.user, hospital=hospital).exists()
    )

    helpful_ids = set()
    if request.user.is_authenticated:
        from reviews.models import ReviewHelpful
        helpful_ids = set(ReviewHelpful.objects.filter(
            user=request.user, review__in=reviews
        ).values_list('review_id', flat=True))

    related_hospitals = Hospital.objects.filter(
        prefecture=hospital.prefecture
    ).exclude(pk=hospital.pk).annotate(
        review_count=Count('reviews', filter=Q(reviews__status='approved')),
        avg_rating=Avg('reviews__overall_rating', filter=Q(reviews__status='approved')),
    ).order_by('-review_count')[:5]

    return render(request, 'hospitals/detail.html', {
        'hospital': hospital,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating else None,
        'avg_salary': round(avg_salary) if avg_salary else None,
        'avg_overtime': round(avg_overtime, 1) if avg_overtime else None,
        'review_count': reviews.count(),
        'job_posts': job_posts,
        'is_favorite': is_favorite,
        'sort': sort,
        'helpful_ids': helpful_ids,
        'related_hospitals': related_hospitals,
    })
