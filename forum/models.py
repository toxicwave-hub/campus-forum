from django.conf import settings
from django.db import models


class Board(models.Model):
    name = models.CharField('板块名称', max_length=100)
    slug = models.SlugField('板块短链接', unique=True)
    description = models.TextField('板块介绍', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '板块'
        verbose_name_plural = '板块'

    def __str__(self):
        return self.name


class Post(models.Model):
    board = models.ForeignKey(
        Board,
        verbose_name='板块',
        on_delete=models.CASCADE,
        related_name='posts',
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
    content = models.TextField('正文')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    view_count = models.PositiveIntegerField('浏览量', default=0)
    is_pinned = models.BooleanField('是否置顶', default=False)

    class Meta:
        verbose_name = '帖子'
        verbose_name_plural = '帖子'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Reply(models.Model):
    post = models.ForeignKey(
        Post,
        verbose_name='帖子',
        on_delete=models.CASCADE,
        related_name='replies',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='作者',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
    )
    content = models.TextField('回复内容')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '回帖'
        verbose_name_plural = '回帖'
        ordering = ['created_at']

    def __str__(self):
        username = self.author.username if self.author else '已注销用户'
        return f'{username}回复了{self.post.title}'


class PostLike(models.Model):
    post = models.ForeignKey(
        Post,
        verbose_name='帖子',
        on_delete=models.CASCADE,
        related_name='likes',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='用户',
        on_delete=models.CASCADE,
        related_name='post_likes',
    )
    created_at = models.DateTimeField('点赞时间', auto_now_add=True)

    class Meta:
        verbose_name = '帖子点赞'
        verbose_name_plural = '帖子点赞'
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user'],
                name='unique_post_like_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user.username}点赞了{self.post.title}'


class ReplyLike(models.Model):
    reply = models.ForeignKey(
        Reply,
        verbose_name='回帖',
        on_delete=models.CASCADE,
        related_name='likes',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='用户',
        on_delete=models.CASCADE,
        related_name='reply_likes',
    )
    created_at = models.DateTimeField('点赞时间', auto_now_add=True)

    class Meta:
        verbose_name = '回帖点赞'
        verbose_name_plural = '回帖点赞'
        constraints = [
            models.UniqueConstraint(
                fields=['reply', 'user'],
                name='unique_reply_like_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user.username}点赞了一条回帖'


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='用户',
        on_delete=models.CASCADE,
        related_name='profile',
    )
    nickname = models.CharField('昵称', max_length=50, blank=True)
    bio = models.TextField('个人简介', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '个人主页'
        verbose_name_plural = '个人主页'

    def __str__(self):
        return self.user.username
