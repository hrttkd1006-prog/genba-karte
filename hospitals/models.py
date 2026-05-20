from django.db import models
from django.utils.text import slugify
import uuid
import time
import requests

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
NOMINATIM_HEADERS = {'User-Agent': 'genba-karte/1.0 (hrttkd1006@gmail.com)'}


def _geocode(query):
    try:
        res = requests.get(NOMINATIM_URL, params={
            'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'jp',
        }, headers=NOMINATIM_HEADERS, timeout=10)
        data = res.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None


PREFECTURE_CHOICES = [
    ('北海道', '北海道'), ('青森県', '青森県'), ('岩手県', '岩手県'), ('宮城県', '宮城県'),
    ('秋田県', '秋田県'), ('山形県', '山形県'), ('福島県', '福島県'), ('茨城県', '茨城県'),
    ('栃木県', '栃木県'), ('群馬県', '群馬県'), ('埼玉県', '埼玉県'), ('千葉県', '千葉県'),
    ('東京都', '東京都'), ('神奈川県', '神奈川県'), ('新潟県', '新潟県'), ('富山県', '富山県'),
    ('石川県', '石川県'), ('福井県', '福井県'), ('山梨県', '山梨県'), ('長野県', '長野県'),
    ('岐阜県', '岐阜県'), ('静岡県', '静岡県'), ('愛知県', '愛知県'), ('三重県', '三重県'),
    ('滋賀県', '滋賀県'), ('京都府', '京都府'), ('大阪府', '大阪府'), ('兵庫県', '兵庫県'),
    ('奈良県', '奈良県'), ('和歌山県', '和歌山県'), ('鳥取県', '鳥取県'), ('島根県', '島根県'),
    ('岡山県', '岡山県'), ('広島県', '広島県'), ('山口県', '山口県'), ('徳島県', '徳島県'),
    ('香川県', '香川県'), ('愛媛県', '愛媛県'), ('高知県', '高知県'), ('福岡県', '福岡県'),
    ('佐賀県', '佐賀県'), ('長崎県', '長崎県'), ('熊本県', '熊本県'), ('大分県', '大分県'),
    ('宮崎県', '宮崎県'), ('鹿児島県', '鹿児島県'), ('沖縄県', '沖縄県'),
]

FACILITY_TYPE_CHOICES = [
    ('hospital', '病院'),
    ('clinic', 'クリニック・診療所'),
    ('lab', '検査センター'),
    ('other', 'その他'),
]


class Hospital(models.Model):
    name = models.CharField('施設名', max_length=200)
    slug = models.SlugField('スラッグ', max_length=250, unique=True, blank=True)
    prefecture = models.CharField('都道府県', max_length=10, choices=PREFECTURE_CHOICES)
    address = models.CharField('住所', max_length=300)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    facility_type = models.CharField('施設種別', max_length=20, choices=FACILITY_TYPE_CHOICES, default='hospital')
    beds = models.PositiveIntegerField('病床数', null=True, blank=True)
    technician_count = models.PositiveIntegerField('技師数（概算）', null=True, blank=True)
    departments = models.TextField('診療科目', blank=True, help_text='カンマ区切りで入力')
    inspection_items = models.TextField('検査項目', blank=True, help_text='カンマ区切りで入力')
    website = models.URLField('ウェブサイト', blank=True)
    lat = models.FloatField('緯度', null=True, blank=True)
    lng = models.FloatField('経度', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '病院・施設'
        verbose_name_plural = '病院・施設'
        ordering = ['prefecture', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f"{self.name}-{self.prefecture}"
            self.slug = slugify(base, allow_unicode=True)
            if not self.slug:
                self.slug = str(uuid.uuid4())[:8]
            original = self.slug
            counter = 1
            while Hospital.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original}-{counter}"
                counter += 1

        # 座標が未取得のとき自動でジオコーディング
        if not self.lat or not self.lng:
            query = self.address or f"{self.name} {self.prefecture}"
            lat, lng = _geocode(query)
            if not lat:
                lat, lng = _geocode(f"{self.name} {self.prefecture}")
            if lat:
                self.lat, self.lng = lat, lng

        super().save(*args, **kwargs)

    def get_average_rating(self):
        from reviews.models import Review
        reviews = Review.objects.filter(hospital=self, status='approved')
        if not reviews.exists():
            return None
        total = sum(r.overall_rating for r in reviews)
        return round(total / reviews.count(), 1)

    def get_review_count(self):
        from reviews.models import Review
        return Review.objects.filter(hospital=self, status='approved').count()

    def get_departments_list(self):
        if self.departments:
            return [d.strip() for d in self.departments.split(',') if d.strip()]
        return []

    def get_inspection_items_list(self):
        if self.inspection_items:
            return [i.strip() for i in self.inspection_items.split(',') if i.strip()]
        return []


FACILITY_REQUEST_STATUS = [
    ('pending', '審査待ち'),
    ('needs_review', '要確認'),
    ('approved', '承認済み'),
    ('rejected', '却下'),
]


class FacilityRequest(models.Model):
    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='facility_requests', verbose_name='申請者'
    )
    # 施設情報
    facility_name = models.CharField('施設名', max_length=200)
    prefecture = models.CharField('都道府県', max_length=10, choices=PREFECTURE_CHOICES)
    address = models.CharField('住所', max_length=300, blank=True)
    facility_type = models.CharField('施設種別', max_length=20, choices=FACILITY_TYPE_CHOICES, default='hospital')

    # レビュー情報（任意）
    overall_rating = models.PositiveSmallIntegerField('総合評価', null=True, blank=True)
    salary_rating = models.PositiveSmallIntegerField('給与評価', null=True, blank=True)
    relationship_rating = models.PositiveSmallIntegerField('人間関係評価', null=True, blank=True)
    education_rating = models.PositiveSmallIntegerField('教育体制評価', null=True, blank=True)
    equipment_rating = models.PositiveSmallIntegerField('設備評価', null=True, blank=True)
    annual_salary = models.PositiveIntegerField('年収（万円）', null=True, blank=True)
    overtime_hours = models.PositiveSmallIntegerField('月残業時間', null=True, blank=True)
    paid_leave_rate = models.PositiveSmallIntegerField('有給取得率（%）', null=True, blank=True)
    technician_count = models.PositiveSmallIntegerField('技師の人数', null=True, blank=True)
    employment_type = models.CharField('雇用形態', max_length=15, blank=True)
    has_oncall = models.BooleanField('オンコールあり', default=False)
    has_night_duty = models.BooleanField('当直あり', default=False)
    has_night_shift = models.BooleanField('夜勤あり', default=False)
    has_blood_sampling = models.BooleanField('採血行為あり', null=True, blank=True)
    work_style = models.CharField('業務スタイル', max_length=15, blank=True)
    oncall_night_frequency = models.CharField('オンコール・夜勤の頻度', max_length=15, blank=True)
    male_ratio = models.PositiveSmallIntegerField('男性技師の割合（0〜10）', null=True, blank=True)
    average_age = models.PositiveSmallIntegerField('平均年齢', null=True, blank=True)
    education_system = models.CharField('教育体制', max_length=10, blank=True)
    equipment_age = models.CharField('機器の新しさ', max_length=10, blank=True)
    research_opportunity = models.CharField('学会・研究の機会', max_length=10, blank=True)
    certification_support = models.CharField('資格サポート', max_length=10, blank=True)
    good_points = models.TextField('良かった点', blank=True)
    concerns = models.TextField('気になった点', blank=True)
    suitable_for = models.TextField('向いている人', blank=True)
    joining_gap = models.TextField('入職後のギャップ', blank=True)

    # 審査
    status = models.CharField('ステータス', max_length=15, choices=FACILITY_REQUEST_STATUS, default='pending')
    admin_note = models.TextField('管理者メモ・質問', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '施設登録申請'
        verbose_name_plural = '施設登録申請'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.facility_name}（{self.prefecture}）"


class Favorite(models.Model):
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='favorites', verbose_name='ユーザー'
    )
    hospital = models.ForeignKey(
        Hospital, on_delete=models.CASCADE,
        related_name='favorited_by', verbose_name='施設'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'お気に入り'
        verbose_name_plural = 'お気に入り'
        unique_together = ('user', 'hospital')

    def __str__(self):
        return f"{self.user.email} → {self.hospital.name}"
