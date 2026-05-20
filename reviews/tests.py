from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from hospitals.models import Hospital
from reviews.models import Review, Objection


def make_hospital():
    return Hospital.objects.create(
        name='テスト病院',
        prefecture='東京都',
        address='東京都新宿区1-1-1',
        facility_type='hospital',
    )


def make_user(email='user@test.com', password='pass1234!xyz'):
    return User.objects.create_user(email=email, password=password)


def make_review(hospital, user, status='approved'):
    return Review.objects.create(
        hospital=hospital,
        user=user,
        overall_rating=4,
        good_points='良い点です',
        concerns='気になる点です',
        suitable_for='向いている人です',
        agreed_to_terms=True,
        status=status,
    )


AI_WHITE = {'judgment': 'white', 'reason': 'テスト用'}


class ReviewCreateTests(TestCase):
    def setUp(self):
        self.hospital = make_hospital()
        self.user = make_user()
        self.url = reverse('review_create', args=[self.hospital.pk])
        self.valid_data = {
            'overall_rating': 4,
            'employment_type': 'full_time',
            'annual_salary': 400,
            'overtime_hours': 20,
            'has_oncall': False,
            'has_night_duty': False,
            'has_night_shift': False,
            'good_points': 'テストの良い点です',
            'concerns': 'テストの気になる点です',
            'suitable_for': 'テストに向いている人です',
            'agreed_to_terms': True,
            'agreed_to_legal': True,
        }

    def test_redirect_to_login_if_anonymous(self):
        res = self.client.get(self.url)
        self.assertRedirects(res, f'/accounts/login/?next={self.url}')

    def test_get_form_when_logged_in(self):
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    @patch('reviews.views.moderate_review', return_value=AI_WHITE)
    def test_post_creates_review(self, _mock):
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.post(self.url, self.valid_data)
        self.assertRedirects(res, reverse('hospital_detail', args=[self.hospital.pk]))
        self.assertEqual(Review.objects.filter(hospital=self.hospital).count(), 1)

    @patch('reviews.views.moderate_review', return_value=AI_WHITE)
    def test_duplicate_review_blocked(self, _mock):
        make_review(self.hospital, self.user)
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.post(self.url, self.valid_data)
        self.assertRedirects(res, reverse('hospital_detail', args=[self.hospital.pk]))
        self.assertEqual(Review.objects.filter(hospital=self.hospital).count(), 1)

    @patch('reviews.views.moderate_review', return_value={'judgment': 'black', 'reason': 'NG'})
    def test_ai_black_makes_review_rejected(self, _mock):
        self.client.login(username='user@test.com', password='pass1234!xyz')
        self.client.post(self.url, self.valid_data)
        review = Review.objects.get(hospital=self.hospital)
        self.assertEqual(review.status, 'rejected')

    @patch('reviews.views.moderate_review', return_value={'judgment': 'gray', 'reason': '要確認'})
    def test_ai_gray_makes_review_pending(self, _mock):
        self.client.login(username='user@test.com', password='pass1234!xyz')
        self.client.post(self.url, self.valid_data)
        review = Review.objects.get(hospital=self.hospital)
        self.assertEqual(review.status, 'pending')


class ObjectionCreateTests(TestCase):
    def setUp(self):
        self.hospital = make_hospital()
        self.user = make_user()
        self.review = make_review(self.hospital, self.user)
        self.url = reverse('objection_create', args=[self.review.pk])
        self.valid_data = {
            'hospital_name': 'テスト病院',
            'contact_email': 'hospital@test.com',
            'reason': '内容が事実と異なります',
        }

    def test_redirect_to_login_if_anonymous(self):
        res = self.client.post(self.url, self.valid_data)
        self.assertRedirects(res, f'/accounts/login/?next={self.url}')

    def test_logged_in_can_submit_objection(self):
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.post(self.url, self.valid_data)
        self.assertRedirects(res, reverse('hospital_detail', args=[self.hospital.pk]))
        self.assertEqual(Objection.objects.count(), 1)

    def test_review_status_becomes_objection(self):
        self.client.login(username='user@test.com', password='pass1234!xyz')
        self.client.post(self.url, self.valid_data)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, 'objection')

    def test_404_for_non_approved_review(self):
        pending_review = make_review(self.hospital, self.user, status='pending')
        self.client.login(username='user@test.com', password='pass1234!xyz')
        url = reverse('objection_create', args=[pending_review.pk])
        res = self.client.post(url, self.valid_data)
        self.assertEqual(res.status_code, 404)


class ObjectionReplyTests(TestCase):
    def setUp(self):
        self.hospital = make_hospital()
        self.reviewer = make_user(email='reviewer@test.com')
        self.review = make_review(self.hospital, self.reviewer)
        self.objection = Objection.objects.create(
            review=self.review,
            hospital_name='テスト病院',
            contact_email='hospital@test.com',
            reason='異議理由',
            status='waiting_reply',
        )
        self.objection.set_reply_deadline()
        self.url = reverse('objection_reply', args=[self.objection.pk])

    def test_redirect_to_login_if_anonymous(self):
        res = self.client.get(self.url)
        self.assertRedirects(res, f'/accounts/login/?next={self.url}')

    def test_logged_in_can_access_reply_page(self):
        self.client.login(username='reviewer@test.com', password='pass1234!xyz')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_post_reply_changes_status_to_pending(self):
        self.client.login(username='reviewer@test.com', password='pass1234!xyz')
        self.client.post(self.url, {'reply': '事実です'})
        self.objection.refresh_from_db()
        self.assertEqual(self.objection.status, 'pending')
