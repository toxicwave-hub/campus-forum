"""Reddit 风格的热度算法 + 投票工具。"""
import math
from datetime import datetime, timezone as dt_tz

from django.db import transaction
from django.db.models import Sum

from .models import Notification, Post, PostVote, Reply, ReplyVote
from .notifications import notify


_EPOCH = datetime(2025, 1, 1, tzinfo=dt_tz.utc)


def hot_score(score, created_at):
    """Reddit hot 算法的简化版。"""
    order = math.log10(max(abs(score), 1))
    sign = 1 if score > 0 else (-1 if score < 0 else 0)
    seconds = (created_at - _EPOCH).total_seconds()
    return round(sign * order + seconds / 45000, 7)


def _refresh_post_score(post):
    agg = post.votes.aggregate(total=Sum('value'))
    post.score = agg['total'] or 0
    post.hot_score = hot_score(post.score, post.created_at)
    post.save(update_fields=['score', 'hot_score'])


def _refresh_reply_score(reply):
    agg = reply.votes.aggregate(total=Sum('value'))
    reply.score = agg['total'] or 0
    reply.save(update_fields=['score'])


@transaction.atomic
def vote_post(user, post, value):
    """value 为 1（赞）/ -1（踩）/ 0（取消）"""
    existing = PostVote.objects.select_for_update().filter(post=post, user=user).first()

    if value == 0:
        if existing:
            existing.delete()
    elif existing:
        if existing.value != value:
            existing.value = value
            existing.save(update_fields=['value'])
    else:
        PostVote.objects.create(post=post, user=user, value=value)
        if value == PostVote.UP and post.author_id and post.author_id != user.id:
            notify(
                recipient=post.author,
                actor=user,
                kind=Notification.KIND_POST_LIKE,
                post=post,
            )

    _refresh_post_score(post)
    return post.score


@transaction.atomic
def vote_reply(user, reply, value):
    existing = ReplyVote.objects.select_for_update().filter(reply=reply, user=user).first()

    if value == 0:
        if existing:
            existing.delete()
    elif existing:
        if existing.value != value:
            existing.value = value
            existing.save(update_fields=['value'])
    else:
        ReplyVote.objects.create(reply=reply, user=user, value=value)
        if value == ReplyVote.UP and reply.author_id and reply.author_id != user.id:
            notify(
                recipient=reply.author,
                actor=user,
                kind=Notification.KIND_REPLY_LIKE,
                post=reply.post,
                reply=reply,
            )

    _refresh_reply_score(reply)
    return reply.score


def get_user_votes(user, posts=None, replies=None):
    """返回 (post_votes_dict, reply_votes_dict)，键是 id，值是 1/-1。"""
    post_votes = {}
    reply_votes = {}
    if not user or not user.is_authenticated:
        return post_votes, reply_votes
    if posts:
        ids = [p.pk for p in posts]
        for v in PostVote.objects.filter(post_id__in=ids, user=user):
            post_votes[v.post_id] = v.value
    if replies:
        ids = [r.pk for r in replies]
        for v in ReplyVote.objects.filter(reply_id__in=ids, user=user):
            reply_votes[v.reply_id] = v.value
    return post_votes, reply_votes
