from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages as flash
from random import randint

from .models import EmailConfirm, User


def send_email_confirmation(user):
    code = randint(100000, 999999)
    EmailConfirm.objects.update_or_create(
        user=user,
        defaults={'code': str(code)}
    )
    try:
        send_mail(
            subject='Тасдиқи почта — Comfort Home',
            message=f'{user.username}, хуш омадед ба Comfort Home! Рамзи тасдиқи шумо: {code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        
        print(e, '=== Хатои фиристодани почта ===')

