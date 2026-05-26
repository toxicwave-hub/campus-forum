from django.contrib import admin

from .models import Board, Post, PostLike, Reply, ReplyLike, UserProfile


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'author', 'created_at', 'view_count', 'is_pinned')
    list_filter = ('board', 'is_pinned', 'created_at')
    search_fields = ('title', 'content', 'board__name', 'author__username')
    date_hierarchy = 'created_at'


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('content', 'post__title', 'author__username')
    date_hierarchy = 'created_at'


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')
    search_fields = ('post__title', 'user__username')
    date_hierarchy = 'created_at'


@admin.register(ReplyLike)
class ReplyLikeAdmin(admin.ModelAdmin):
    list_display = ('reply', 'user', 'created_at')
    search_fields = ('reply__content', 'reply__post__title', 'user__username')
    date_hierarchy = 'created_at'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'created_at')
    search_fields = ('user__username', 'nickname', 'bio')
    date_hierarchy = 'created_at'
