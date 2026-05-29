from django.db.models import Q

from .models import Conversation, Message, Notification


def unread_notifications(request):
    if request.user.is_authenticated:
        notif_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        msg_count = Message.objects.filter(
            conversation__in=Conversation.objects.filter(
                Q(user_a=request.user) | Q(user_b=request.user)
            ),
            is_read=False,
        ).exclude(sender=request.user).count()
    else:
        notif_count = 0
        msg_count = 0
    return {
        'unread_notifications_count': notif_count,
        'unread_messages_count': msg_count,
    }
