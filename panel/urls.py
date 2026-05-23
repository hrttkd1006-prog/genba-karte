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
    path('articles/', views.article_list_panel, name='panel_article_list'),
    path('articles/create/', views.article_create, name='panel_article_create'),
    path('articles/<int:pk>/edit/', views.article_edit, name='panel_article_edit'),
    path('articles/<int:pk>/delete/', views.article_delete, name='panel_article_delete'),
    path('job-posts/', views.job_posts_panel, name='panel_job_posts'),
    path('job-posts/<int:pk>/action/', views.job_post_action, name='panel_job_post_action'),
    path('server-logs/', views.server_logs, name='panel_server_logs'),
]
