from django.contrib import admin

from .models import (
    Attachment, Board, BoardModerator, BoardSubscription, Bookmark,
    Conversation, Follow, LinkPreview, Message, Notification, Post, PostVote,
    Reply, ReplyBookmark, ReplyVote, Report, UserProfile,
)


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'author', 'status', 'score', 'view_count', 'is_pinned', 'is_nsfw', 'created_at')
    list_filter = ('board', 'status', 'is_pinned', 'is_nsfw', 'created_at')
    search_fields = ('title', 'content', 'board__name', 'author__username')
    date_hierarchy = 'created_at'


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'parent', 'score', 'is_removed', 'created_at')
    search_fields = ('content', 'post__title', 'author__username')
    date_hierarchy = 'created_at'


@admin.register(PostVote)
class PostVoteAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'value', 'created_at')


@admin.register(ReplyVote)
class ReplyVoteAdmin(admin.ModelAdmin):
    list_display = ('reply', 'user', 'value', 'created_at')


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followee', 'created_at')


@admin.register(BoardSubscription)
class BoardSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'board', 'created_at')


@admin.register(BoardModerator)
class BoardModeratorAdmin(admin.ModelAdmin):
    list_display = ('board', 'user', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user_a', 'user_b', 'last_message_at')
    search_fields = ('user_a__username', 'user_b__username')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'content_preview', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('content', 'sender__username', 'conversation__user_a__username', 'conversation__user_b__username')

    @admin.display(description='内容预览')
    def content_preview(self, obj):
        return obj.content[:80]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('kind', 'reporter', 'reason', 'status', 'created_at')
    list_filter = ('kind', 'status')
    search_fields = ('reason', 'detail')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'original_name', 'size', 'post', 'reply', 'uploader', 'created_at')


@admin.register(LinkPreview)
class LinkPreviewAdmin(admin.ModelAdmin):
    list_display = ('url', 'title', 'site_name', 'fetched_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'karma', 'created_at')
    search_fields = ('user__username', 'user__email', 'nickname')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'kind', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')



@admin.register(ReplyBookmark)
class ReplyBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'reply', 'created_at')
