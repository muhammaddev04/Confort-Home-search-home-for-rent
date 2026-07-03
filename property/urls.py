from django.urls import path
from . import views

urlpatterns = [
     path('', views.home, name='home'),
     path('about/', views.about, name='about'),
     path('search/', views.property_search, name='property_search'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('api/properties-map/', views.properties_map_data, name='properties_map_data'),
    path('dashboard/', views.landlord_dashboard, name='landlord_dashboard'), 
    path('my-properties/', views.property_list, name='property_list'),
    path('create-property/', views.create_property, name='create_property'),
    path('update-property/<int:pk>/', views.update_property, name='update_property'),
    path('delete-property/<int:pk>/', views.delete_property, name='delete_property'),
    path('propertyimages/', views.propertyimage_list, name='propertyimages_list'),
]