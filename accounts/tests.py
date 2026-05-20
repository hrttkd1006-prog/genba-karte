from django.test import TestCase
from django.urls import reverse
from accounts.models import User


def make_user(email='user@test.com', password='pass1234!xyz'):
    return User.objects.create_user(email=email, password=password)


class StaticPageTests(TestCase):
    def test_terms_page(self):
        res = self.client.get(reverse('terms'))
        self.assertEqual(res.status_code, 200)

    def test_privacy_page(self):
        res = self.client.get(reverse('privacy'))
        self.assertEqual(res.status_code, 200)

    def test_tokusho_page(self):
        res = self.client.get(reverse('tokusho'))
        self.assertEqual(res.status_code, 200)

    def test_contact_page(self):
        res = self.client.get(reverse('contact'))
        self.assertEqual(res.status_code, 200)


class ProfileTests(TestCase):
    def test_profile_requires_login(self):
        res = self.client.get(reverse('profile'))
        self.assertRedirects(res, f'/accounts/login/?next=/profile/')

    def test_profile_accessible_when_logged_in(self):
        make_user()
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.get(reverse('profile'))
        self.assertEqual(res.status_code, 200)

    def test_profile_shows_email(self):
        make_user(email='myemail@test.com')
        self.client.login(username='myemail@test.com', password='pass1234!xyz')
        res = self.client.get(reverse('profile'))
        self.assertContains(res, 'myemail@test.com')


class TopPageTests(TestCase):
    def test_top_page_returns_200(self):
        res = self.client.get(reverse('top'))
        self.assertEqual(res.status_code, 200)

    def test_top_shows_hospital_admin_section_to_anonymous(self):
        res = self.client.get(reverse('top'))
        self.assertContains(res, '病院・施設の方へ')

    def test_top_hides_hospital_section_from_general_user(self):
        make_user()
        self.client.login(username='user@test.com', password='pass1234!xyz')
        res = self.client.get(reverse('top'))
        self.assertNotContains(res, '病院・施設の方へ')
