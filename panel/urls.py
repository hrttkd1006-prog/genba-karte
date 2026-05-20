from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='panel_dashboard'),
    path('facility-requests/', views.facility_requests, name='panel_facility_requests'),
    path('facility-requests/<int:pk>/', views.facility_request_detail, name='panel_facility_request_detail'),
    path('facility-requests/<int:pk>/action/', views.facility_request_action, name='panel_facility_request_action'),
    path('contacts/', views.contacts, name='panel_contacts'),
    path('contacts/<int:pk>/read/', views.contact_mark_read, name='panel_contact_mark_read'),
    path('job-applications/', views.job_applications, name='panel_job_applications'),
    path('job-applications/<int:pk>/action/', views.job_application_action, name='panel_job_application_action'),
    path('objections/', views.objections, name='panel_objections'),
    path('objections/<int:pk>/action/', views.objection_action, name='panel_objection_action'),
    path('reviews/', views.reviews, name='panel_reviews'),
    path('reviews/<int:pk>/', views.review_detail, name='panel_review_detail'),
    path('reviews/<int:pk>/action/', views.review_action, name='panel_review_action'),
    path('users/', views.users, name='panel_users'),
    path('users/<int:pk>/action/', views.user_action, name='panel_user_action'),
    path('change-password/', views.change_password, name='panel_change_password'),
]
