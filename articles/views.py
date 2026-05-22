from django.shortcuts import render, get_object_or_404
from .models import Article, ARTICLE_CATEGORY_CHOICES


def article_list(request):
    articles = Article.objects.filter(is_published=True)
    category = request.GET.get('category', '')
    if category:
        articles = articles.filter(category=category)
    return render(request, 'articles/list.html', {
        'articles': articles,
        'categories': ARTICLE_CATEGORY_CHOICES,
        'selected_category': category,
    })


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    related = Article.objects.filter(
        is_published=True, category=article.category
    ).exclude(pk=article.pk)[:3]
    return render(request, 'articles/detail.html', {
        'article': article,
        'related': related,
    })
