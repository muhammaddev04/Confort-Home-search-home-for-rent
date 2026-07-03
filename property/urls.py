from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('search/', views.PropertySearchView.as_view(), name='property_search'),
    path('property/<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('api/properties-map/', views.properties_map_data, name='properties_map_data'),

    path('dashboard/', views.LandlordDashboardView.as_view(), name='landlord_dashboard'),
    # path('inbox/', views.inbox, name='inbox'),

    path('my-properties/', views.PropertyListView.as_view(), name='property_list'),
    path('create-property/', views.PropertyCreateView.as_view(), name='create_property'),
    path('update-property/<int:pk>/', views.PropertyUpdateView.as_view(), name='update_property'),
    path('delete-property/<int:pk>/', views.PropertyDeleteView.as_view(), name='delete_property'),

    path('propertyimages/', views.PropertyImageListView.as_view(), name='propertyimages_list'),
    path('create-propertyimages/', views.PropertyImageCreateView.as_view(), name='create_propertyimages'),
    path('update-propertyimages/<int:pk>/', views.PropertyImageUpdateView.as_view(), name='update_propertyimages'),
    path('delete-propertyimages/<int:pk>/', views.PropertyImageDeleteView.as_view(), name='delete_propertyimages'),

    path('favorites/', views.FavoriteListView.as_view(), name='favorite_list'),
    path('toggle-favorite/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
    path('delete-favorite/<int:pk>/', views.FavoriteDeleteView.as_view(), name='delete_favorite'),

    path('ask-groq/', views.ask_groq_view, name='ask_groq'),
]