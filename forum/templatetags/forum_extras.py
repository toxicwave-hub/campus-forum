from django import template
from django.utils.safestring import mark_safe

from ..link_preview import extract_first_url, get_or_fetch_preview
from ..markdown_utils import render_markdown
from ..models import UserProfile, avatar_color_for

register = template.Library()


@register.filter(name='markdown')
def markdown_filter(value):
    return render_markdown(value or '')


@register.filter(name='get_item')
def get_item(d, key):
    """模板里从 dict 取值，找不到返回 0。"""
    if d is None:
        return 0
    try:
        return d.get(key, 0)
    except AttributeError:
        return 0


@register.simple_tag
def avatar(user, size=36):
    """渲染圆形头像。优先使用上传的图片，否则字母 + 颜色。"""
    if user is None:
        return _letter_avatar('?', avatar_color_for('anonymous'), size)

    initial = (getattr(user, 'username', None) or '?')[0].upper()
    color = avatar_color_for(getattr(user, 'username', None) or 'user')
    avatar_url = ''
    try:
        profile = user.profile
    except (UserProfile.DoesNotExist, AttributeError):
        profile = None
    if profile:
        initial = profile.initial
        color = profile.color
        if profile.avatar:
            avatar_url = profile.avatar.url

    if avatar_url:
        style = f'width:{size}px;height:{size}px;'
        return mark_safe(
            f'<img class="avatar avatar-img" src="{avatar_url}" alt="{initial}" '
            f'style="{style}" loading="lazy">'
        )
    return _letter_avatar(initial, color, size)


@register.simple_tag
def avatar_for_name(name, size=36):
    initial = (name or '?')[0].upper()
    color = avatar_color_for(name or 'anonymous')
    return _letter_avatar(initial, color, size)


def _letter_avatar(initial, color, size):
    style = (
        f'background:{color};width:{size}px;height:{size}px;'
        f'font-size:{max(12, int(size * 0.45))}px;'
    )
    return mark_safe(
        f'<span class="avatar" style="{style}">{initial}</span>'
    )


@register.simple_tag
def link_preview_for(text):
    """从一段文字里提取第一个 URL，返回 LinkPreview 或 None。"""
    url = extract_first_url(text or '')
    if not url:
        return None
    try:
        return get_or_fetch_preview(url)
    except Exception:
        return None
