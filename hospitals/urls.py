from django.urls import path
from . import views
from accounts.views import top

urlpatterns = [
    path('', top, name='top'),
    path('hospitals/', views.hospital_list, name='hospital_list'),
    path('hospitals/map/', views.hospital_map, name='hospital_map'),
    path('hospitals/request/', views.facility_request_create, name='facility_request_create'),
    path('hospitals/favorites/', views.favorite_list, name='favorite_list'),
    path('hospitals/<int:pk>/', views.hospital_detail, name='hospital_detail'),
    path('hospitals/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
]
