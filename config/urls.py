from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from hospitals.sitemaps import HospitalSitemap, ArticleSitemap, StaticSitemap
from two_factor.urls import core as tf_core, profile as tf_profile

sitemaps = {
    'hospitals': HospitalSitemap,
    'articles': ArticleSitemap,
    'static': StaticSitemap,
}

_panel_prefix = getattr(settings, 'PANEL_URL_PREFIX', 'manage-gk2025')

urlpatterns = [
    # path('admin/', admin.site.urls),  # /manage/ に移行のため無効化
    path('', include((tf_core + tf_profile, 'two_factor'))),
    path('accounts/', include('allauth.urls')),
    path('', include('hospitals.urls')),
    path('reviews/', include('reviews.urls')),
    path('jobs/', include('jobs.urls')),
    path('', include('accounts.urls')),
    path('articles/', include('articles.urls')),
    path(f'{_panel_prefix}/', include('panel.urls')),
    path('line/', include('line_bot.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
