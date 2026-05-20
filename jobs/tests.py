from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from hospitals.models import Hospital
from jobs.models import HospitalAdminProfile, JobPost, HospitalAdminApplication


def make_hospital():
    return Hospital.objects.create(
        name='テスト病院',
        prefecture='東京都',
        address='東京都新宿区1-1-1',
        facility_type='hospital',
    )


def make_user(email='user@test.com', password='pass1234!xyz', is_hospital_admin=False):
    return User.objects.create_user(
        email=email, password=password, is_hospital_admin=is_hospital_admin
    )


def make_admin_user_with_profile(hospital, active=False):
    user = make_user(email='admin@test.com', is_hospital_admin=True)
    profile = HospitalAdminProfile.objects.create(
        user=user,
        hospital=hospital,
        subscription_status='active' if active else 'inactive',
    )
    return user, profile


class ForHospitalsLandingTests(TestCase):
    def test_accessible_to_anonymous(self):
        res = self.client.get(reverse('for_hospitals'))
        self.assertEqual(res.status_code, 200)

    def test_shows_steps(self):
        res = self.client.get(reverse('for_hospitals'))
        self.assertContains(res, '申し込みフォームに入力')


class HospitalRegisterTests(TestCase):
    def test_get_form(self):
        res = self.client.get(reverse('hospital_register'))
        self.assertEqual(res.status_code, 200)

    def test_post_creates_application(self):
        data = {
            'facility_name': 'テスト病院',
            'contact_name': '山田太郎',
            'email': 'contact@hospital.com',
            'phone': '03-1234-5678',
            'official_url': 'https://www.hospital.example.jp',
            'message': '',
            'agreed_to_terms': True,
        }
        res = self.client.post(reverse('hospital_register'), data)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'テスト病院')
        self.assertEqual(HospitalAdminApplication.objects.count(), 1)

    def test_post_without_agreement_fails(self):
        data = {
            'facility_name': 'テスト病院',
            'contact_name': '山田太郎',
            'email': 'contact@hospital.com',
            'phone': '03-1234-5678',
            'agreed_to_terms': False,
        }
        self.client.post(reverse('hospital_register'), data)
        self.assertEqual(HospitalAdminApplication.objects.count(), 0)


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.url = reverse('hospital_admin_dashboard')

    def test_anonymous_redirected_to_login(self):
        res = self.client.get(self.url)
        self.assertRedirects(res, reverse('account_login'))

    def test_general_user_redirected_to_top(self):
        make_user()
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.get(self.url)
        self.assertRedirects(res, reverse('top'))

    def test_hospital_admin_can_access(self):
        hospital = make_hospital()
        make_admin_user_with_profile(hospital)
        self.client.login(username='admin@test.com', password='pass1234!xyz')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)


class JobPostTests(TestCase):
    def setUp(self):
        self.hospital = make_hospital()
        self.user, self.profile = make_admin_user_with_profile(self.hospital, active=True)
        self.client.login(username='admin@test.com', password='pass1234!xyz')

    def test_create_job_post(self):
        data = {
            'title': '臨床検査技師 募集',
            'employment_type': 'full_time',
            'salary_min': 350,
            'salary_max': 500,
            'description': '仕事内容です',
            'requirements': '応募条件です',
            'benefits': '福利厚生です',
            'is_active': True,
        }
        res = self.client.post(reverse('job_post_create'), data)
        self.assertRedirects(res, reverse('hospital_admin_dashboard'))
        self.assertEqual(JobPost.objects.count(), 1)

    def test_create_blocked_without_subscription(self):
        self.profile.subscription_status = 'inactive'
        self.profile.save()
        res = self.client.get(reverse('job_post_create'))
        self.assertRedirects(res, reverse('hospital_admin_dashboard'))

    def test_edit_job_post(self):
        job = JobPost.objects.create(
            hospital=self.hospital,
            created_by=self.user,
            title='旧タイトル',
            employment_type='full_time',
            description='旧内容',
        )
        data = {
            'title': '新タイトル',
            'employment_type': 'full_time',
            'description': '新しい内容',
            'is_active': True,
        }
        res = self.client.post(reverse('job_post_edit', args=[job.pk]), data)
        self.assertRedirects(res, reverse('hospital_admin_dashboard'))
        job.refresh_from_db()
        self.assertEqual(job.title, '新タイトル')

    def test_delete_job_post(self):
        job = JobPost.objects.create(
            hospital=self.hospital,
            created_by=self.user,
            title='削除対象',
            employment_type='full_time',
            description='内容',
        )
        res = self.client.post(reverse('job_post_delete', args=[job.pk]))
        self.assertRedirects(res, reverse('hospital_admin_dashboard'))
        self.assertEqual(JobPost.objects.count(), 0)

    def test_edit_blocked_for_other_user(self):
        other_user = make_user(email='other@test.com', is_hospital_admin=True)
        HospitalAdminProfile.objects.create(
            user=other_user, hospital=self.hospital, subscription_status='active'
        )
        job = JobPost.objects.create(
            hospital=self.hospital,
            created_by=other_user,
            title='他人の求人',
            employment_type='full_time',
            description='内容',
        )
        res = self.client.post(reverse('job_post_edit', args=[job.pk]), {'title': '改ざん'})
        self.assertEqual(res.status_code, 404)
