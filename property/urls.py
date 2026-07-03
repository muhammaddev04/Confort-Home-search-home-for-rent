from django.urls import path
from . import views

urlpatterns = [
     path('', views.home, name='home'),
     path('about/', views.about, name='about'),
     path('search/', views.property_search, name='property_search'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
]