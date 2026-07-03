from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('confirm/', views.confirm_email, name='confirm_email'),
    path('resend-confirmation/', views.resend_confirmation, name='resend_confirmation'),
]