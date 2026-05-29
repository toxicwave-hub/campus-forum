from .models import Notification


def notify(recipient, actor, kind, post=None, reply=None):
    """生成一条通知。自己给自己点赞/回复时不通知。"""
    if recipient is None:
        return None
    if actor is not None and recipient == actor:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        kind=kind,
        post=post,
        reply=reply,
    )
