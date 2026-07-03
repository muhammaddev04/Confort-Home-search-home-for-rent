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



def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')

        if not username or not email or not password1 or not password2 or not role:
            return render(request, 'register.html', {'error': 'Лутфан ҳамаи майдонҳоро пур кунед'})

        if password1 != password2:
            return render(request, 'register.html', {'error': 'Рамзҳо мувофиқ нестанд'})

        if len(password1) < 8:
            return render(request, 'register.html', {'error': 'Рамз бояд ҳадди ақал 8 аломат бошад'})

        if role not in ['landlord', 'tenant']:
            return render(request, 'register.html', {'error': 'Нақши нодуруст'})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Ин номи корбар аллакай вуҷуд дорад'})

        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Ин почта аллакай сабт шудааст'})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            role=role,
            is_active=False,
        )

        send_email_confirmation(user)
        return render(request, 'confirm.html', {'user': user})

    return render(request, 'register.html')