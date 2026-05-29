from rest_framework import serializers

from .models import Board, Post, Reply, UserProfile, avatar_color_for


class UserMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    def _profile(self, obj):
        try:
            return obj.profile
        except UserProfile.DoesNotExist:
            return None

    def get_nickname(self, obj):
        p = self._profile(obj)
        return (p.nickname if p else '') or obj.username

    def get_avatar(self, obj):
        p = self._profile(obj)
        if p and p.avatar:
            return p.avatar.url
        return ''

    def get_color(self, obj):
        p = self._profile(obj)
        return p.color if p else avatar_color_for(obj.username)


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ('id', 'name', 'slug', 'description', 'icon', 'created_at')


class PostSerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)
    board = BoardSerializer(read_only=True)
    reply_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Post
        fields = (
            'id', 'title', 'content', 'cover_image',
            'author', 'board', 'created_at', 'updated_at',
            'view_count', 'is_pinned', 'is_nsfw', 'score', 'hot_score',
            'reply_count',
        )
        read_only_fields = ('view_count', 'score', 'hot_score', 'created_at', 'updated_at')


class ReplySerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)

    class Meta:
        model = Reply
        fields = ('id', 'post', 'parent', 'author', 'content', 'score', 'created_at')
        read_only_fields = ('score', 'created_at')
