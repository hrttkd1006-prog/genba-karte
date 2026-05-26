from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid


ARTICLE_CATEGORY_CHOICES = [
    ('tips', '転職Tips'),
    ('student', '学生・就活'),
    ('knowledge', '業界知識'),
    ('facility', '施設紹介'),
    ('news', 'お知らせ'),
    ('other', 'その他'),
]


class Article(models.Model):
    title = models.CharField('タイトル', max_length=200)
    slug = models.SlugField('スラッグ', max_length=220, unique=True, blank=True)
    category = models.CharField('カテゴリ', max_length=20, choices=ARTICLE_CATEGORY_CHOICES, default='tips')
    body = models.TextField('本文')
    thumbnail = models.ImageField('サムネイル', upload_to='articles/', blank=True, null=True)
    is_published = models.BooleanField('公開', default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='articles', verbose_name='著者'
    )
    view_count = models.PositiveIntegerField('PV数', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField('公開日時', null=True, blank=True)

    class Meta:
        verbose_name = '記事'
        verbose_name_plural = '記事'
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)  # ASCII only
            if not base:
                base = f"article-{uuid.uuid4().hex[:10]}"
            self.slug = base
            counter = 1
            while Article.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
