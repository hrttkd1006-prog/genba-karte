from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from hospitals.models import Hospital
from reviews.models import Review


def make_hospital(**kwargs):
    defaults = {
        'name': 'テスト病院',
        'prefecture': '東京都',
        'address': '東京都新宿区1-1-1',
        'facility_type': 'hospital',
    }
    defaults.update(kwargs)
    return Hospital.objects.create(**defaults)


def make_user(email='user@test.com', password='pass1234!xyz'):
    return User.objects.create_user(email=email, password=password)


class HospitalListTests(TestCase):
    def test_list_page_returns_200(self):
        res = self.client.get(reverse('hospital_list'))
        self.assertEqual(res.status_code, 200)

    def test_list_shows_hospitals(self):
        make_hospital(name='北海道病院', prefecture='北海道', address='札幌市1-1')
        make_hospital(name='大阪病院', prefecture='大阪府', address='大阪市1-1')
        res = self.client.get(reverse('hospital_list'))
        self.assertContains(res, '北海道病院')
        self.assertContains(res, '大阪病院')

    def test_list_filter_by_prefecture(self):
        make_hospital(name='北海道病院', prefecture='北海道', address='札幌市1-1')
        make_hospital(name='大阪病院', prefecture='大阪府', address='大阪市1-1')
        res = self.client.get(reverse('hospital_list') + '?prefecture=北海道')
        self.assertContains(res, '北海道病院')
        self.assertNotContains(res, '大阪病院')

    def test_list_filter_by_keyword(self):
        make_hospital(name='東京大学病院', prefecture='東京都', address='東京都文京区1-1')
        make_hospital(name='大阪大学病院', prefecture='大阪府', address='大阪市1-1')
        res = self.client.get(reverse('hospital_list') + '?keyword=東京')
        self.assertContains(res, '東京大学病院')
        self.assertNotContains(res, '大阪大学病院')


class HospitalDetailTests(TestCase):
    def setUp(self):
        self.hospital = make_hospital()
        self.user = make_user()
        self.url = reverse('hospital_detail', args=[self.hospital.pk])

    def test_detail_page_returns_200(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_detail_shows_hospital_name(self):
        res = self.client.get(self.url)
        self.assertContains(res, 'テスト病院')

    def test_detail_shows_chips_to_anonymous(self):
        Review.objects.create(
            hospital=self.hospital,
            user=self.user,
            overall_rating=4,
            good_points='良い点です',
            concerns='気になる点です',
            suitable_for='向いている人です',
            agreed_to_terms=True,
            status='approved',
            annual_salary=400,
            overtime_hours=20,
        )
        res = self.client.get(self.url)
        self.assertContains(res, '年収 400万円')
        self.assertContains(res, '残業 20h/月')

    def test_detail_blurs_text_for_anonymous(self):
        Review.objects.create(
            hospital=self.hospital,
            user=self.user,
            overall_rating=4,
            good_points='これは良い点です',
            concerns='これは気になる点です',
            suitable_for='向いている人です',
            agreed_to_terms=True,
            status='approved',
        )
        res = self.client.get(self.url)
        self.assertNotContains(res, 'これは良い点です')
        self.assertContains(res, 'filter:blur')

    def test_detail_shows_text_for_logged_in_user(self):
        Review.objects.create(
            hospital=self.hospital,
            user=self.user,
            overall_rating=4,
            good_points='これは良い点です',
            concerns='これは気になる点です',
            suitable_for='向いている人です',
            agreed_to_terms=True,
            status='approved',
        )
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.get(self.url)
        self.assertContains(res, 'これは良い点です')

    def test_detail_shows_no_review_message_when_empty(self):
        res = self.client.get(self.url)
        self.assertContains(res, 'まだレビューがありません')

    def test_pending_review_not_shown(self):
        Review.objects.create(
            hospital=self.hospital,
            user=self.user,
            overall_rating=4,
            good_points='審査中の良い点',
            concerns='審査中の気になる点',
            suitable_for='向いている人',
            agreed_to_terms=True,
            status='pending',
        )
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.get(self.url)
        self.assertNotContains(res, '審査中の良い点')
