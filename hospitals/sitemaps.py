from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Hospital


class HospitalSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Hospital.objects.all()

    def location(self, obj):
        return reverse('hospital_detail', args=[obj.pk])

    def lastmod(self, obj):
        return obj.updated_at


class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return ['top', 'hospital_list', 'terms', 'privacy', 'contact']

    def location(self, item):
        return reverse(item)
