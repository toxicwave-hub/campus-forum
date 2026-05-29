import hashlib
import os
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


AVATAR_PALETTE = [
    '#0f766e', '#1d4ed8', '#7c3aed', '#db2777', '#dc2626',
    '#ea580c', '#ca8a04', '#16a34a', '#0891b2', '#4338ca',
]


def avatar_color_for(text):
    if not text:
        return AVATAR_PALETTE[0]
    digest = hashlib.md5(text.encode('utf-8')).hexdigest()
    return AVATAR_PALETTE[int(digest, 16) % len(AVATAR_PALETTE)]


def _upload_path(instance, filename, prefix):
    ext = os.path.splitext(filename)[1].lower()
    new_name = f'{uuid.uuid4().hex}{ext}'
    date_dir = timezone.now().strftime('%Y/%m')
    return f'{prefix}/{date_dir}/{new_name}'


def avatar_upload_to(instance, filename):
    return _upload_path(instance, filename, 'avatars')


def cover_upload_to(instance, filename):
    return _upload_path(instance, filename, 'covers')


def attachment_upload_to(instance, filename):
    return _upload_path(instance, filename, 'attachments')


def message_upload_to(instance, filename):
    return _upload_path(instance, filename, 'messages')


class Board(models.Model):
    name = models.CharField('板块名称', max_length=100)
    slug = models.SlugField('板块短链接', unique=True)
    description = models.TextField('板块介绍', blank=True)
    icon = models.CharField('图标', max_length=8, blank=True, default='💬')
    accent_color = models.CharField('主色（HEX）', max_length=16, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '板块'
        verbose_name_plural = '板块'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('board_detail', args=[self.slug])


class Post(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_REMOVED = 'removed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_PUBLISHED, '已发布'),
        (STATUS_REMOVED, '已删除'),
    ]

    board = models.ForeignKey(
        Board, verbose_name='板块', on_delete=models.CASCADE, related_name='posts'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='作者',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
    )
    title = models.CharField('标题', max_length=200)
    content = models.TextField('正文', blank=True)
    cover_image = models.ImageField(
        '封面图', upload_to=cover_upload_to, blank=True, null=True
    )
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default=STATUS_PUBLISHED)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    view_count = models.PositiveIntegerField('浏览量', default=0)
    is_pinned = models.BooleanField('是否置顶', default=False)
    is_nsfw = models.BooleanField('NSFW', default=False)
    score = models.IntegerField('得分（赞 - 踩）', default=0, db_index=True)
    hot_score = models.FloatField('热度', default=0.0, db_index=True)

    class Meta:
        verbose_name = '帖子'
        verbose_name_plural = '帖子'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['board', '-is_pinned', '-created_at']),
            models.Index(fields=['board', '-is_pinned', '-hot_score']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.pk])


class Reply(models.Model):
    post = models.ForeignKey(
        Post, verbose_name='帖子', on_delete=models.CASCADE, related_name='replies'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='作者',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
    )
    parent = models.ForeignKey(
        'self',
        verbose_name='回复对象',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
    )
    content = models.TextField('回复内容')
    score = models.IntegerField('得分', default=0)
    is_removed = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '回帖'
        verbose_name_plural = '回帖'
        ordering = ['created_at']

    def __str__(self):
        username = self.author.username if self.author else '已注销用户'
        return f'{username}回复了{self.post.title}'


class PostVote(models.Model):
    UP = 1
    DOWN = -1
    VALUE_CHOICES = [(UP, '赞'), (DOWN, '踩')]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_votes'
    )
    value = models.SmallIntegerField('投票', choices=VALUE_CHOICES)
    created_at = models.DateTimeField('时间', auto_now_add=True)

    class Meta:
        verbose_name = '帖子投票'
        verbose_name_plural = '帖子投票'
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_post_vote_per_user'),
        ]


class ReplyVote(models.Model):
    UP = 1
    DOWN = -1
    VALUE_CHOICES = [(UP, '赞'), (DOWN, '踩')]

    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reply_votes'
    )
    value = models.SmallIntegerField('投票', choices=VALUE_CHOICES)
    created_at = models.DateTimeField('时间', auto_now_add=True)

    class Meta:
        verbose_name = '回帖投票'
        verbose_name_plural = '回帖投票'
        constraints = [
            models.UniqueConstraint(fields=['reply', 'user'], name='unique_reply_vote_per_user'),
        ]


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks'
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField('收藏时间', auto_now_add=True)

    class Meta:
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_bookmark_per_user_post'),
        ]


class ReplyBookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reply_bookmarks'
    )
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField('收藏时间', auto_now_add=True)

    class Meta:
        verbose_name = '回帖收藏'
        verbose_name_plural = '回帖收藏'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'reply'], name='unique_reply_bookmark_per_user'),
        ]


class Follow(models.Model):
    """用户关注用户。"""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following'
    )
    followee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers'
    )
    created_at = models.DateTimeField('关注时间', auto_now_add=True)

    class Meta:
        verbose_name = '关注'
        verbose_name_plural = '关注'
        constraints = [
            models.UniqueConstraint(fields=['follower', 'followee'], name='unique_follow'),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F('followee')),
                name='no_self_follow',
            ),
        ]
        ordering = ['-created_at']


class BoardSubscription(models.Model):
    """订阅板块。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='board_subscriptions'
    )
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='subscriptions')
    created_at = models.DateTimeField('订阅时间', auto_now_add=True)

    class Meta:
        verbose_name = '板块订阅'
        verbose_name_plural = '板块订阅'
        constraints = [
            models.UniqueConstraint(fields=['user', 'board'], name='unique_board_subscription'),
        ]
        ordering = ['-created_at']


class BoardModerator(models.Model):
    """板块版主。"""

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='moderators')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='moderated_boards'
    )
    created_at = models.DateTimeField('任命时间', auto_now_add=True)

    class Meta:
        verbose_name = '版主'
        verbose_name_plural = '版主'
        constraints = [
            models.UniqueConstraint(fields=['board', 'user'], name='unique_board_moderator'),
        ]


class Conversation(models.Model):
    """两人之间的私信会话（按用户对去重）。"""

    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_a',
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_b',
    )
    last_message_at = models.DateTimeField('最后消息时间', default=timezone.now, db_index=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '会话'
        verbose_name_plural = '会话'
        ordering = ['-last_message_at']
        constraints = [
            models.UniqueConstraint(fields=['user_a', 'user_b'], name='unique_conversation_pair'),
            models.CheckConstraint(
                condition=models.Q(user_a__lt=models.F('user_b')),
                name='conversation_user_order',
            ),
        ]

    @classmethod
    def between(cls, u1, u2):
        """获取或创建两个用户之间的会话，user_a 永远是 id 小的那个。"""
        if u1.id == u2.id:
            raise ValueError('不能给自己发私信')
        a, b = (u1, u2) if u1.id < u2.id else (u2, u1)
        obj, _ = cls.objects.get_or_create(user_a=a, user_b=b)
        return obj

    def other(self, user):
        return self.user_b if user.id == self.user_a_id else self.user_a


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
    )
    content = models.TextField('内容', blank=True)
    image = models.ImageField('图片', upload_to=message_upload_to, blank=True, null=True)
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('发送时间', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '私信'
        verbose_name_plural = '私信'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender}: {self.content[:20]}'


class Report(models.Model):
    """举报。"""

    KIND_POST = 'post'
    KIND_REPLY = 'reply'
    KIND_USER = 'user'
    KIND_CHOICES = [(KIND_POST, '帖子'), (KIND_REPLY, '回帖'), (KIND_USER, '用户')]

    STATUS_OPEN = 'open'
    STATUS_RESOLVED = 'resolved'
    STATUS_DISMISSED = 'dismissed'
    STATUS_CHOICES = [
        (STATUS_OPEN, '待处理'),
        (STATUS_RESOLVED, '已处理'),
        (STATUS_DISMISSED, '已驳回'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports',
    )
    kind = models.CharField('类型', max_length=16, choices=KIND_CHOICES)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True, related_name='reports'
    )
    reply = models.ForeignKey(
        Reply, on_delete=models.CASCADE, null=True, blank=True, related_name='reports'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports_against',
    )
    reason = models.CharField('原因', max_length=200)
    detail = models.TextField('详细描述', blank=True)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN)
    handler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_reports',
    )
    created_at = models.DateTimeField('举报时间', auto_now_add=True)
    handled_at = models.DateTimeField('处理时间', null=True, blank=True)

    class Meta:
        verbose_name = '举报'
        verbose_name_plural = '举报'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_kind_display()}: {self.reason}'


class Attachment(models.Model):
    KIND_IMAGE = 'image'
    KIND_VIDEO = 'video'
    KIND_FILE = 'file'
    KIND_CHOICES = [
        (KIND_IMAGE, '图片'),
        (KIND_VIDEO, '视频'),
        (KIND_FILE, '文件'),
    ]

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments'
    )
    reply = models.ForeignKey(
        Reply, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments'
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attachments',
    )
    kind = models.CharField('类型', max_length=16, choices=KIND_CHOICES)
    file = models.FileField('文件', upload_to=attachment_upload_to)
    original_name = models.CharField('原始文件名', max_length=200, blank=True)
    size = models.PositiveIntegerField('文件大小', default=0)
    width = models.PositiveIntegerField('宽', null=True, blank=True)
    height = models.PositiveIntegerField('高', null=True, blank=True)
    created_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        verbose_name = '附件'
        verbose_name_plural = '附件'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_kind_display()}: {self.original_name or self.file.name}'

    @property
    def url(self):
        return self.file.url if self.file else ''

    @property
    def size_display(self):
        size = self.size or 0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}' if unit != 'B' else f'{size} {unit}'
            size /= 1024
        return f'{size:.1f} TB'


class LinkPreview(models.Model):
    url = models.URLField('链接', max_length=500, unique=True)
    title = models.CharField('标题', max_length=300, blank=True)
    description = models.TextField('描述', blank=True)
    image = models.URLField('封面图', max_length=500, blank=True)
    site_name = models.CharField('站点名', max_length=100, blank=True)
    fetched_at = models.DateTimeField('抓取时间', auto_now=True)

    class Meta:
        verbose_name = '链接预览'
        verbose_name_plural = '链接预览'

    def __str__(self):
        return self.title or self.url


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='用户',
        on_delete=models.CASCADE,
        related_name='profile',
    )
    nickname = models.CharField('昵称', max_length=50, blank=True)
    bio = models.TextField('个人简介', blank=True)
    avatar = models.ImageField(
        '头像', upload_to=avatar_upload_to, blank=True, null=True
    )
    avatar_color = models.CharField('头像颜色', max_length=16, blank=True)
    karma = models.IntegerField('Karma', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '个人主页'
        verbose_name_plural = '个人主页'

    def __str__(self):
        return self.user.username

    @property
    def display_name(self):
        return self.nickname or self.user.username

    @property
    def color(self):
        return self.avatar_color or avatar_color_for(self.user.username)

    @property
    def initial(self):
        name = self.nickname or self.user.username or '?'
        return name[0].upper()


class Notification(models.Model):
    KIND_REPLY = 'reply'
    KIND_REPLY_TO_REPLY = 'reply_to_reply'
    KIND_POST_LIKE = 'post_like'
    KIND_REPLY_LIKE = 'reply_like'
    KIND_MENTION = 'mention'
    KIND_FOLLOW = 'follow'
    KIND_MESSAGE = 'message'

    KIND_CHOICES = [
        (KIND_REPLY, '回复了你的帖子'),
        (KIND_REPLY_TO_REPLY, '回复了你的回帖'),
        (KIND_POST_LIKE, '点赞了你的帖子'),
        (KIND_REPLY_LIKE, '点赞了你的回帖'),
        (KIND_MENTION, '提到了你'),
        (KIND_FOLLOW, '关注了你'),
        (KIND_MESSAGE, '给你发了私信'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='接收者',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='触发者',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_notifications',
    )
    kind = models.CharField('类型', max_length=32, choices=KIND_CHOICES)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    reply = models.ForeignKey(
        Reply,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        actor = self.actor.username if self.actor else '系统'
        return f'{actor} -> {self.recipient.username} ({self.kind})'

    def get_absolute_url(self):
        if self.kind == self.KIND_FOLLOW and self.actor:
            return reverse('user_profile', args=[self.actor.username])
        if self.kind == self.KIND_MESSAGE and self.actor:
            return reverse('conversation', args=[self.actor.username])
        if self.post_id:
            return reverse('post_detail', args=[self.post_id])
        return reverse('notifications')
