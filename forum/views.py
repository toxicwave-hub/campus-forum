from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render

from .models import Board, Post, PostLike, Reply, ReplyLike, UserProfile


def home(request):
    boards = Board.objects.all().order_by('created_at')
    return render(request, 'forum/home.html', {'boards': boards})


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
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is None:
            error = '用户名或密码错误。'
        else:
            login(request, user)
            if next_url:
                return redirect(next_url)
            return redirect('home')

    return render(request, 'forum/login.html', {'error': error, 'next_url': next_url})


def logout_view(request):
    logout(request)
    return redirect('home')


def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    posts = (
        Post.objects.filter(author=profile_user)
        .select_related('board')
        .annotate(reply_count=Count('replies'), like_count=Count('likes'))
        .order_by('-created_at')
    )
    reply_count = Reply.objects.filter(author=profile_user).count()
    return render(
        request,
        'forum/user_profile.html',
        {
            'profile_user': profile_user,
            'profile': profile,
            'posts': posts,
            'post_count': posts.count(),
            'reply_count': reply_count,
        },
    )


def board_detail(request, slug):
    board = get_object_or_404(Board, slug=slug)
    posts = (
        board.posts.select_related('author')
        .annotate(reply_count=Count('replies'), like_count=Count('likes'))
        .order_by('-is_pinned', '-created_at')
    )
    return render(request, 'forum/board_detail.html', {'board': board, 'posts': posts})


@login_required(login_url='login')
def new_post(request, slug):
    board = get_object_or_404(Board, slug=slug)
    error = ''

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if not title or not content:
            error = '标题和正文不能为空。'
        else:
            post = Post.objects.create(
                board=board,
                author=request.user,
                title=title,
                content=content,
            )
            return redirect('post_detail', pk=post.pk)

    return render(request, 'forum/post_form.html', {'board': board, 'error': error})


def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related('board', 'author'), pk=pk)
    reply_error = ''

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        content = request.POST.get('content', '').strip()
        if not content:
            reply_error = '回帖内容不能为空。'
        else:
            Reply.objects.create(post=post, author=request.user, content=content)
            return redirect('post_detail', pk=post.pk)
    else:
        Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
        post.refresh_from_db(fields=['view_count'])

    replies = (
        post.replies.select_related('author')
        .annotate(like_count=Count('likes'))
        .order_by('created_at')
    )
    post_like_count = post.likes.count()
    user_liked_post = False
    liked_reply_ids = set()

    if request.user.is_authenticated:
        user_liked_post = post.likes.filter(user=request.user).exists()
        liked_reply_ids = set(
            ReplyLike.objects.filter(reply__post=post, user=request.user)
            .values_list('reply_id', flat=True)
        )

    return render(
        request,
        'forum/post_detail.html',
        {
            'post': post,
            'replies': replies,
            'post_like_count': post_like_count,
            'user_liked_post': user_liked_post,
            'liked_reply_ids': liked_reply_ids,
            'reply_error': reply_error,
        },
    )


@login_required(login_url='login')
def toggle_post_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like = PostLike.objects.filter(post=post, user=request.user).first()

    if like:
        like.delete()
    else:
        PostLike.objects.create(post=post, user=request.user)

    return redirect('post_detail', pk=post.pk)


@login_required(login_url='login')
def toggle_reply_like(request, pk):
    reply = get_object_or_404(Reply.objects.select_related('post'), pk=pk)
    like = ReplyLike.objects.filter(reply=reply, user=request.user).first()

    if like:
        like.delete()
    else:
        ReplyLike.objects.create(reply=reply, user=request.user)

    return redirect('post_detail', pk=reply.post.pk)
