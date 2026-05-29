from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Board, Bookmark, Post, Reply
from .serializers import BoardSerializer, PostSerializer, ReplySerializer
from .voting import vote_post, vote_reply


class BoardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Board.objects.all().order_by('created_at')
    serializer_class = BoardSerializer
    lookup_field = 'slug'


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = (
            Post.objects.filter(status=Post.STATUS_PUBLISHED)
            .select_related('board', 'author')
            .annotate(reply_count=Count('replies'))
        )
        sort = self.request.query_params.get('sort', 'hot')
        order = {
            'hot': ('-is_pinned', '-hot_score', '-created_at'),
            'new': ('-is_pinned', '-created_at'),
            'top': ('-is_pinned', '-score', '-created_at'),
        }.get(sort, ('-is_pinned', '-hot_score', '-created_at'))
        return qs.order_by(*order)

    def perform_create(self, serializer):
        slug = self.request.data.get('board_slug')
        board = Board.objects.get(slug=slug)
        serializer.save(author=self.request.user, board=board, status=Post.STATUS_PUBLISHED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def vote(self, request, pk=None):
        post = self.get_object()
        try:
            value = int(request.data.get('value', 0))
        except (TypeError, ValueError):
            return Response({'error': 'invalid'}, status=400)
        if value not in (-1, 0, 1):
            return Response({'error': 'invalid'}, status=400)
        score = vote_post(request.user, post, value)
        return Response({'score': score, 'value': value})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, pk=None):
        post = self.get_object()
        bm = Bookmark.objects.filter(user=request.user, post=post).first()
        if bm:
            bm.delete()
            return Response({'bookmarked': False})
        Bookmark.objects.create(user=request.user, post=post)
        return Response({'bookmarked': True})


class ReplyViewSet(viewsets.ModelViewSet):
    serializer_class = ReplySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Reply.objects.filter(is_removed=False).select_related('author', 'post')
        post_id = self.request.query_params.get('post')
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs.order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def vote(self, request, pk=None):
        reply = self.get_object()
        try:
            value = int(request.data.get('value', 0))
        except (TypeError, ValueError):
            return Response({'error': 'invalid'}, status=400)
        if value not in (-1, 0, 1):
            return Response({'error': 'invalid'}, status=400)
        score = vote_reply(request.user, reply, value)
        return Response({'score': score, 'value': value})
