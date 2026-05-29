from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, F, Max, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from .forms import (
    LoginForm, MessageForm, PostForm, ProfileForm, RegisterForm,
    ReplyForm, ReportForm, SearchForm,
)
from .markdown_utils import extract_mentions
from .models import (
    Attachment, Board, BoardModerator, BoardSubscription, Bookmark,
    Conversation, Follow, Message, Notification, Post, PostVote,
    Reply, ReplyVote, Report, UserProfile,
)
from .notifications import notify
from .uploads import create_attachment
from .voting import get_user_votes, vote_post, vote_reply


PAGE_SIZE = 10

SORT_OPTIONS = {
    'hot': ('-is_pinned', '-hot_score', '-created_at'),
    'new': ('-is_pinned', '-created_at'),
    'top': ('-is_pinned', '-score', '-created_at'),
    'discussed': ('-is_pinned', '-reply_count', '-created_at'),
}


def _published_posts():
    return Post.objects.filter(status=Post.STATUS_PUBLISHED)


def _sort_posts_qs(qs, sort):
    return qs.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS['hot']))


def _is_moderator(user, board):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return BoardModerator.objects.filter(board=board, user=user).exists()


# ----------- 首页 / 板块 / 搜索 -----------

def home(request):
    sort = request.GET.get('sort', 'hot')
    feed = request.GET.get('feed', 'all')
    boards = Board.objects.annotate(post_count=Count('posts')).order_by('created_at')
    posts_qs = (
        _published_posts().select_related('board', 'author')
        .annotate(reply_count=Count('replies'))
    )

    if feed == 'subscribed' and request.user.is_authenticated:
        sub_ids = BoardSubscription.objects.filter(user=request.user).values_list('board_id', flat=True)
        posts_qs = posts_qs.filter(board_id__in=list(sub_ids))
    elif feed == 'following' and request.user.is_authenticated:
        following_ids = Follow.objects.filter(follower=request.user).values_list('followee_id', flat=True)
        posts_qs = posts_qs.filter(author_id__in=list(following_ids))

    posts_qs = _sort_posts_qs(posts_qs, sort)
    paginator = Paginator(posts_qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    posts = list(page_obj.object_list)
    user_post_votes, _ = get_user_votes(request.user, posts=posts)

    return render(request, 'forum/home.html', {
        'boards': boards, 'page_obj': page_obj, 'posts': posts,
        'user_post_votes': user_post_votes, 'sort': sort, 'feed': feed,
    })


def board_detail(request, slug):
    board = get_object_or_404(Board, slug=slug)
    sort = request.GET.get('sort', 'hot')
    posts_qs = (
        board.posts.filter(status=Post.STATUS_PUBLISHED)
        .select_related('author')
        .annotate(reply_count=Count('replies'))
    )
    posts_qs = _sort_posts_qs(posts_qs, sort)
    paginator = Paginator(posts_qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    posts = list(page_obj.object_list)
    user_post_votes, _ = get_user_votes(request.user, posts=posts)

    is_subscribed = False
    if request.user.is_authenticated:
        is_subscribed = BoardSubscription.objects.filter(user=request.user, board=board).exists()

    return render(request, 'forum/board_detail.html', {
        'board': board, 'page_obj': page_obj, 'posts': posts,
        'user_post_votes': user_post_votes, 'sort': sort,
        'is_subscribed': is_subscribed,
        'is_moderator': _is_moderator(request.user, board),
        'subscriber_count': board.subscriptions.count(),
        'moderators': list(board.moderators.select_related('user')),
    })


def search(request):
    form = SearchForm(request.GET or None)
    query = (request.GET.get('q') or '').strip()
    page_obj = None
    posts = []
    user_post_votes = {}
    if query:
        posts_qs = (
            _published_posts()
            .filter(Q(title__icontains=query) | Q(content__icontains=query))
            .select_related('board', 'author')
            .annotate(reply_count=Count('replies'))
            .order_by('-created_at')
        )
        paginator = Paginator(posts_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get('page'))
        posts = list(page_obj.object_list)
        user_post_votes, _ = get_user_votes(request.user, posts=posts)
    return render(request, 'forum/search.html', {
        'form': form, 'query': query, 'posts': posts,
        'page_obj': page_obj, 'user_post_votes': user_post_votes,
    })


# ----------- 账户 -----------

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, '注册成功，欢迎加入校园论坛。')
        return redirect('home')
    return render(request, 'forum/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, '欢迎回来。')
        return redirect(next_url or 'home')
    return render(request, 'forum/login.html', {'form': form, 'next_url': next_url})


def logout_view(request):
    logout(request)
    messages.info(request, '已退出登录。')
    return redirect('home')


def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    posts_qs = (
        Post.objects.filter(author=profile_user, status=Post.STATUS_PUBLISHED)
        .select_related('board')
        .annotate(reply_count=Count('replies'))
        .order_by('-created_at')
    )
    paginator = Paginator(posts_qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    posts = list(page_obj.object_list)
    user_post_votes, _ = get_user_votes(request.user, posts=posts)
    reply_count = Reply.objects.filter(author=profile_user).count()

    is_following = False
    if request.user.is_authenticated and request.user != profile_user:
        is_following = Follow.objects.filter(
            follower=request.user, followee=profile_user
        ).exists()

    follower_count = Follow.objects.filter(followee=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()

    return render(request, 'forum/user_profile.html', {
        'profile_user': profile_user, 'profile': profile,
        'page_obj': page_obj, 'posts': posts,
        'user_post_votes': user_post_votes,
        'post_count': posts_qs.count(),
        'reply_count': reply_count,
        'is_following': is_following,
        'follower_count': follower_count,
        'following_count': following_count,
    })


@login_required(login_url='login')
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '个人主页已更新。')
        return redirect('user_profile', username=request.user.username)
    return render(request, 'forum/profile_edit.html', {'form': form})


@login_required(login_url='login')
def my_drafts(request):
    qs = (
        Post.objects.filter(author=request.user, status=Post.STATUS_DRAFT)
        .select_related('board')
        .order_by('-updated_at')
    )
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'forum/drafts.html', {
        'page_obj': page_obj, 'drafts': page_obj.object_list,
    })


# ----------- 关注 / 订阅 -----------

@login_required(login_url='login')
@require_POST
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({'error': '不能关注自己'}, status=400)
    follow, created = Follow.objects.get_or_create(follower=request.user, followee=target)
    if not created:
        follow.delete()
        is_following = False
    else:
        is_following = True
        notify(recipient=target, actor=request.user, kind=Notification.KIND_FOLLOW)
    follower_count = Follow.objects.filter(followee=target).count()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_following': is_following, 'follower_count': follower_count})
    return redirect('user_profile', username=username)


@login_required(login_url='login')
def followers_list(request, username):
    profile_user = get_object_or_404(User, username=username)
    qs = (
        Follow.objects.filter(followee=profile_user)
        .select_related('follower__profile')
        .order_by('-created_at')
    )
    return render(request, 'forum/follow_list.html', {
        'profile_user': profile_user, 'kind': 'followers', 'follows': qs,
    })


@login_required(login_url='login')
def following_list(request, username):
    profile_user = get_object_or_404(User, username=username)
    qs = (
        Follow.objects.filter(follower=profile_user)
        .select_related('followee__profile')
        .order_by('-created_at')
    )
    return render(request, 'forum/follow_list.html', {
        'profile_user': profile_user, 'kind': 'following', 'follows': qs,
    })


@login_required(login_url='login')
@require_POST
def toggle_subscribe(request, slug):
    board = get_object_or_404(Board, slug=slug)
    sub, created = BoardSubscription.objects.get_or_create(user=request.user, board=board)
    if not created:
        sub.delete()
        subscribed = False
    else:
        subscribed = True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'subscribed': subscribed,
            'subscriber_count': board.subscriptions.count(),
        })
    return redirect('board_detail', slug=slug)


# ----------- 帖子 -----------

def _process_mentions(text, *, actor, post=None, reply=None):
    names = extract_mentions(text)
    if not names:
        return
    users = User.objects.filter(username__in=names).exclude(pk=actor.pk)
    for u in users:
        notify(recipient=u, actor=actor, kind=Notification.KIND_MENTION, post=post, reply=reply)


def _save_uploads(files, *, post=None, reply=None, uploader=None, request=None):
    saved = 0
    for f in files or []:
        try:
            create_attachment(f, post=post, reply=reply, uploader=uploader)
            saved += 1
        except ValidationError as e:
            if request:
                messages.warning(request, f'{f.name}: {e.message}')
    return saved


@login_required(login_url='login')
def new_post(request, slug):
    board = get_object_or_404(Board, slug=slug)
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.board = board
        post.author = request.user
        if form.cleaned_data.get('save_as_draft'):
            post.status = Post.STATUS_DRAFT
        else:
            post.status = Post.STATUS_PUBLISHED
            post.published_at = timezone.now()
        post.save()
        files = form.cleaned_data.get('attachments') or []
        _save_uploads(files, post=post, uploader=request.user, request=request)
        if post.status == Post.STATUS_PUBLISHED:
            _process_mentions(post.content, actor=request.user, post=post)
            messages.success(request, '帖子发布成功。')
            return redirect('post_detail', pk=post.pk)
        messages.info(request, '草稿已保存。')
        return redirect('drafts')
    return render(request, 'forum/post_form.html', {'board': board, 'form': form})


@login_required(login_url='login')
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id and not request.user.is_staff and not _is_moderator(request.user, post.board):
        return HttpResponseForbidden('无权编辑这个帖子。')
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        was_draft = post.status == Post.STATUS_DRAFT
        post = form.save(commit=False)
        if form.cleaned_data.get('save_as_draft'):
            post.status = Post.STATUS_DRAFT
        elif was_draft:
            post.status = Post.STATUS_PUBLISHED
            post.published_at = timezone.now()
        post.save()
        files = form.cleaned_data.get('attachments') or []
        _save_uploads(files, post=post, uploader=request.user, request=request)
        messages.success(request, '帖子已更新。')
        return redirect('post_detail', pk=post.pk)
    return render(request, 'forum/post_form.html', {'board': post.board, 'form': form, 'editing': True})


@login_required(login_url='login')
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id and not request.user.is_staff and not _is_moderator(request.user, post.board):
        return HttpResponseForbidden('无权删除这个帖子。')
    if request.method == 'POST':
        board_slug = post.board.slug
        post.delete()
        messages.success(request, '帖子已删除。')
        return redirect('board_detail', slug=board_slug)
    return render(request, 'forum/confirm_delete.html', {
        'object_label': '帖子', 'object_text': post.title,
        'cancel_url': reverse('post_detail', args=[post.pk]),
    })


def _viewed_recently(request, post_id):
    key = 'viewed_posts'
    viewed = request.session.get(key, {})
    now_ts = int(timezone.now().timestamp())
    last = viewed.get(str(post_id))
    if last and now_ts - last < 60 * 30:
        return True
    viewed[str(post_id)] = now_ts
    cutoff = now_ts - 60 * 60 * 24
    viewed = {k: v for k, v in viewed.items() if v >= cutoff}
    request.session[key] = viewed
    return False


def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related('board', 'author').prefetch_related('attachments'),
        pk=pk,
    )
    if post.status == Post.STATUS_DRAFT and post.author_id != getattr(request.user, 'id', None):
        return HttpResponseForbidden('草稿只有作者可见。')

    reply_form = ReplyForm()
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        reply_form = ReplyForm(request.POST, request.FILES)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.post = post
            reply.author = request.user
            parent_id = request.POST.get('parent')
            parent = None
            if parent_id:
                parent = Reply.objects.filter(pk=parent_id, post=post).first()
            reply.parent = parent
            reply.save()
            files = reply_form.cleaned_data.get('attachments') or []
            _save_uploads(files, reply=reply, uploader=request.user, request=request)
            if parent and parent.author_id:
                notify(recipient=parent.author, actor=request.user,
                       kind=Notification.KIND_REPLY_TO_REPLY, post=post, reply=reply)
            elif post.author_id:
                notify(recipient=post.author, actor=request.user,
                       kind=Notification.KIND_REPLY, post=post, reply=reply)
            _process_mentions(reply.content, actor=request.user, post=post, reply=reply)
            messages.success(request, '回帖发布成功。')
            return redirect('post_detail', pk=post.pk)
    else:
        if not _viewed_recently(request, post.pk):
            Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
            post.refresh_from_db(fields=['view_count'])

    replies_qs = (
        post.replies.filter(is_removed=False)
        .select_related('author', 'parent', 'parent__author')
        .prefetch_related('attachments')
        .order_by('created_at')
    )
    replies = list(replies_qs)
    user_post_votes, user_reply_votes = get_user_votes(
        request.user, posts=[post], replies=replies
    )
    user_vote_for_post = user_post_votes.get(post.pk, 0)
    user_bookmarked = False
    user_bookmarked_reply_ids = set()
    if request.user.is_authenticated:
        user_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()
        from .models import ReplyBookmark
        user_bookmarked_reply_ids = set(
            ReplyBookmark.objects.filter(user=request.user, reply__in=replies)
            .values_list('reply_id', flat=True)
        )

    return render(request, 'forum/post_detail.html', {
        'post': post, 'replies': replies,
        'user_vote_for_post': user_vote_for_post,
        'user_reply_votes': user_reply_votes,
        'user_bookmarked': user_bookmarked,
        'user_bookmarked_reply_ids': user_bookmarked_reply_ids,
        'reply_form': reply_form,
        'is_moderator': _is_moderator(request.user, post.board),
    })


@login_required(login_url='login')
def reply_edit(request, pk):
    reply = get_object_or_404(Reply.objects.select_related('post'), pk=pk)
    if reply.author_id != request.user.id and not request.user.is_staff and not _is_moderator(request.user, reply.post.board):
        return HttpResponseForbidden('无权编辑这条回帖。')
    form = ReplyForm(request.POST or None, request.FILES or None, instance=reply)
    if request.method == 'POST' and form.is_valid():
        reply = form.save()
        files = form.cleaned_data.get('attachments') or []
        _save_uploads(files, reply=reply, uploader=request.user, request=request)
        messages.success(request, '回帖已更新。')
        return redirect('post_detail', pk=reply.post.pk)
    return render(request, 'forum/reply_edit.html', {'form': form, 'reply': reply})


@login_required(login_url='login')
def reply_delete(request, pk):
    reply = get_object_or_404(Reply.objects.select_related('post'), pk=pk)
    if reply.author_id != request.user.id and not request.user.is_staff and not _is_moderator(request.user, reply.post.board):
        return HttpResponseForbidden('无权删除这条回帖。')
    if request.method == 'POST':
        post_pk = reply.post.pk
        reply.delete()
        messages.success(request, '回帖已删除。')
        return redirect('post_detail', pk=post_pk)
    return render(request, 'forum/confirm_delete.html', {
        'object_label': '回帖', 'object_text': reply.content[:60],
        'cancel_url': reverse('post_detail', args=[reply.post.pk]),
    })


# ----------- 投票 -----------

def _parse_vote_value(raw):
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return None
    return v if v in (-1, 0, 1) else None


@login_required(login_url='login')
@require_POST
def post_vote_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    value = _parse_vote_value(request.POST.get('value'))
    if value is None:
        return JsonResponse({'error': 'invalid value'}, status=400)
    score = vote_post(request.user, post, value)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'score': score, 'value': value})
    return redirect('post_detail', pk=post.pk)


@login_required(login_url='login')
@require_POST
def reply_vote_view(request, pk):
    reply = get_object_or_404(Reply.objects.select_related('post'), pk=pk)
    value = _parse_vote_value(request.POST.get('value'))
    if value is None:
        return JsonResponse({'error': 'invalid value'}, status=400)
    score = vote_reply(request.user, reply, value)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'score': score, 'value': value})
    return redirect('post_detail', pk=reply.post.pk)


# ----------- 收藏 -----------

@login_required(login_url='login')
@require_POST
def toggle_bookmark(request, pk):
    post = get_object_or_404(Post, pk=pk)
    bookmark = Bookmark.objects.filter(user=request.user, post=post).first()
    if bookmark:
        bookmark.delete()
        bookmarked = False
    else:
        Bookmark.objects.create(user=request.user, post=post)
        bookmarked = True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'bookmarked': bookmarked})
    return redirect('post_detail', pk=post.pk)


@login_required(login_url='login')
def my_bookmarks(request):
    qs = (
        Bookmark.objects.filter(user=request.user)
        .select_related('post', 'post__board', 'post__author')
        .order_by('-created_at')
    )
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'forum/bookmarks.html', {
        'page_obj': page_obj, 'bookmarks': page_obj.object_list,
    })


@login_required(login_url='login')
@require_POST
def attachment_delete(request, pk):
    att = get_object_or_404(Attachment, pk=pk)
    if att.uploader_id != request.user.id and not request.user.is_staff:
        return HttpResponseForbidden('无权删除附件。')
    redirect_to = request.POST.get('next') or reverse('home')
    att.file.delete(save=False)
    att.delete()
    return redirect(redirect_to)


# ----------- 通知 -----------

@login_required(login_url='login')
def notifications_view(request):
    qs = (
        Notification.objects.filter(recipient=request.user)
        .select_related('actor', 'post', 'reply')
        .order_by('-created_at')
    )
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'forum/notifications.html', {
        'page_obj': page_obj, 'notifications': page_obj.object_list,
    })


@login_required(login_url='login')
@require_POST
def notifications_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, '已全部标为已读。')
    return redirect('notifications')


@login_required(login_url='login')
def notification_open(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    return redirect(notif.get_absolute_url())


# ----------- 私信 -----------

@login_required(login_url='login')
def conversations_list(request):
    qs = (
        Conversation.objects.filter(Q(user_a=request.user) | Q(user_b=request.user))
        .select_related('user_a__profile', 'user_b__profile')
        .order_by('-last_message_at')
    )
    convs = []
    for c in qs:
        other = c.other(request.user)
        last = c.messages.order_by('-created_at').first()
        unread = c.messages.filter(is_read=False).exclude(sender=request.user).count()
        convs.append({
            'conv': c, 'other': other, 'last': last, 'unread': unread,
        })
    return render(request, 'forum/conversations.html', {'conversations': convs})


@login_required(login_url='login')
def conversation_view(request, username):
    other = get_object_or_404(User, username=username)
    if other == request.user:
        messages.error(request, '不能给自己发私信。')
        return redirect('conversations')
    try:
        conv = Conversation.between(request.user, other)
    except ValueError:
        return redirect('conversations')

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            if not (msg.content and msg.content.strip()) and not msg.image:
                messages.warning(request, '内容不能为空。')
                return redirect('conversation', username=username)
            msg.conversation = conv
            msg.sender = request.user
            msg.save()
            conv.last_message_at = msg.created_at
            conv.save(update_fields=['last_message_at'])
            notify(recipient=other, actor=request.user,
                   kind=Notification.KIND_MESSAGE)
            return redirect('conversation', username=username)
    else:
        form = MessageForm()

    # 标记对方发来的消息为已读
    conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    msgs = list(conv.messages.select_related('sender').order_by('created_at'))
    return render(request, 'forum/conversation.html', {
        'conv': conv, 'other': other, 'messages_list': msgs, 'form': form,
    })


@login_required(login_url='login')
@require_GET
def conversations_unread_count(request):
    n = Message.objects.filter(
        conversation__in=Conversation.objects.filter(
            Q(user_a=request.user) | Q(user_b=request.user)
        ),
        is_read=False,
    ).exclude(sender=request.user).count()
    return JsonResponse({'unread': n})


# ----------- 举报 -----------

@login_required(login_url='login')
def report_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = ReportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        report = form.save(commit=False)
        report.reporter = request.user
        report.kind = Report.KIND_POST
        report.post = post
        report.save()
        messages.success(request, '举报已提交，版主会尽快处理。')
        return redirect('post_detail', pk=post.pk)
    return render(request, 'forum/report.html', {
        'form': form, 'target_label': f'帖子《{post.title}》',
        'cancel_url': reverse('post_detail', args=[post.pk]),
    })


@login_required(login_url='login')
def report_reply(request, pk):
    reply = get_object_or_404(Reply.objects.select_related('post'), pk=pk)
    form = ReportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        report = form.save(commit=False)
        report.reporter = request.user
        report.kind = Report.KIND_REPLY
        report.reply = reply
        report.save()
        messages.success(request, '举报已提交。')
        return redirect('post_detail', pk=reply.post.pk)
    return render(request, 'forum/report.html', {
        'form': form, 'target_label': '一条回帖',
        'cancel_url': reverse('post_detail', args=[reply.post.pk]),
    })


# ----------- 版主面板 -----------

@login_required(login_url='login')
def mod_dashboard(request, slug):
    board = get_object_or_404(Board, slug=slug)
    if not _is_moderator(request.user, board):
        return HttpResponseForbidden('需要版主权限。')

    open_reports = (
        Report.objects.filter(
            Q(post__board=board) | Q(reply__post__board=board),
            status=Report.STATUS_OPEN,
        )
        .select_related('reporter', 'post', 'reply')
        .order_by('-created_at')
    )
    return render(request, 'forum/mod_dashboard.html', {
        'board': board, 'reports': open_reports,
    })


@login_required(login_url='login')
@require_POST
def mod_report_resolve(request, pk):
    report = get_object_or_404(Report, pk=pk)
    board = report.post.board if report.post else (report.reply.post.board if report.reply else None)
    if not board or not _is_moderator(request.user, board):
        return HttpResponseForbidden('需要版主权限。')
    action = request.POST.get('action')
    if action == 'remove' and report.post:
        report.post.status = Post.STATUS_REMOVED
        report.post.save(update_fields=['status'])
    elif action == 'remove' and report.reply:
        report.reply.is_removed = True
        report.reply.save(update_fields=['is_removed'])
    report.status = Report.STATUS_RESOLVED if action == 'remove' else Report.STATUS_DISMISSED
    report.handler = request.user
    report.handled_at = timezone.now()
    report.save(update_fields=['status', 'handler', 'handled_at'])
    messages.success(request, '已处理。')
    return redirect('mod_dashboard', slug=board.slug)


# ----------- @ 自动补全 API -----------

@login_required(login_url='login')
@require_GET
def user_search_api(request):
    q = (request.GET.get('q') or '').strip()
    if len(q) < 1:
        return JsonResponse({'results': []})
    qs = (
        User.objects.filter(username__istartswith=q)
        .exclude(pk=request.user.pk)
        .select_related('profile')[:8]
    )
    results = [{
        'username': u.username,
        'nickname': getattr(getattr(u, 'profile', None), 'nickname', '') or u.username,
        'color': getattr(getattr(u, 'profile', None), 'color', '#0ff'),
        'initial': (u.username or '?')[0].upper(),
    } for u in qs]
    return JsonResponse({'results': results})


# ----------- 兼容老 URL：跳转到 allauth -----------

def login_redirect(request):
    qs = request.META.get('QUERY_STRING', '')
    return redirect('/accounts/login/' + (('?' + qs) if qs else ''))


def register_redirect(request):
    return redirect('/accounts/signup/')


def logout_redirect(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, '已退出登录。')
        return redirect('home')
    return redirect('/accounts/logout/')


# ----------- 回帖收藏 -----------

@login_required(login_url='login')
@require_POST
def toggle_reply_bookmark(request, pk):
    from .models import ReplyBookmark
    reply = get_object_or_404(Reply.objects.select_related('post'), pk=pk)
    bm = ReplyBookmark.objects.filter(user=request.user, reply=reply).first()
    if bm:
        bm.delete()
        bookmarked = False
    else:
        ReplyBookmark.objects.create(user=request.user, reply=reply)
        bookmarked = True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'bookmarked': bookmarked})
    return redirect('post_detail', pk=reply.post.pk)
