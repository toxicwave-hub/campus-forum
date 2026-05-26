from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render


def home(request):
    return render(request, 'forum/home.html')


def register(request):
    error = ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not username or not password or not password_confirm:
            error = '请填写用户名、密码和确认密码。'
        elif password != password_confirm:
            error = '两次输入的密码不一致。'
        elif User.objects.filter(username=username).exists():
            error = '这个用户名已经存在，请换一个。'
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            login(request, user)
            return redirect('home')

    return render(request, 'forum/register.html', {'error': error})


def login_view(request):
    error = ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is None:
            error = '用户名或密码错误。'
        else:
            login(request, user)
            return redirect('home')

    return render(request, 'forum/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('home')


def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    return render(request, 'forum/user_profile.html', {'profile_user': profile_user})
