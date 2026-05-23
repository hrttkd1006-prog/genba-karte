from django.urls import path
from . import views

urlpatterns = [
    path('write/<int:hospital_pk>/', views.review_create, name='review_create'),
    path('<int:pk>/edit/', views.review_edit, name='review_edit'),
    path('<int:pk>/delete/', views.review_delete, name='review_delete'),
    path('<int:pk>/helpful/', views.toggle_helpful, name='review_helpful'),
    path('recent/', views.recent_reviews, name='recent_reviews'),
    path('objection/<int:review_id>/', views.objection_create, name='objection_create'),
    path('objection-reply/<int:objection_id>/', views.objection_reply, name='objection_reply'),
]
