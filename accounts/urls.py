from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('tokusho/', views.tokusho, name='tokusho'),
    path('contact/', views.contact, name='contact'),
]
