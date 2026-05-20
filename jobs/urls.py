from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('for-hospitals/', views.for_hospitals_landing, name='for_hospitals'),
    path('for-hospitals/register/', views.hospital_register, name='hospital_register'),
    path('apply/', views.hospital_admin_apply, name='hospital_admin_apply'),
    path('dashboard/', views.hospital_admin_dashboard, name='hospital_admin_dashboard'),
    path('new/', views.job_post_create, name='job_post_create'),
    path('<int:pk>/edit/', views.job_post_edit, name='job_post_edit'),
    path('<int:pk>/delete/', views.job_post_delete, name='job_post_delete'),
    path('checkout/', views.create_checkout_session, name='create_checkout_session'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]
