import re

import bleach
import markdown as md
from django.urls import reverse
from django.utils.safestring import mark_safe


ALLOWED_TAGS = [
    'p', 'br', 'hr', 'pre', 'code', 'blockquote',
    'strong', 'em', 'b', 'i', 'u', 's', 'del',
    'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'span', 'div',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title', 'rel', 'target', 'data-mention'],
    'img': ['src', 'alt', 'title', 'loading'],
    'span': ['class', 'style'],
    'code': ['class'],
    'pre': ['class'],
    'div': ['class'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

MENTION_REGEX = re.compile(r'(^|[\s（(])@([A-Za-z0-9_\u4e00-\u9fa5]{2,30})')


def _linkify_mentions(text):
    def replace(m):
        prefix = m.group(1)
        name = m.group(2)
        url = reverse('user_profile', args=[name])
        return f'{prefix}<a href="{url}" class="mention" data-mention="{name}">@{name}</a>'

    return MENTION_REGEX.sub(replace, text)


def render_markdown(text):
    if not text:
        return ''
    html = md.markdown(
        text,
        extensions=[
            'fenced_code',
            'codehilite',
            'tables',
            'nl2br',
            'sane_lists',
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'codehilite',
                'guess_lang': False,
                'noclasses': False,
            },
        },
        output_format='html',
    )
    html = _linkify_mentions(html)
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = bleach.linkify(cleaned)
    return mark_safe(cleaned)


def extract_mentions(text):
    """返回所有被 @ 的用户名（去重，保持顺序）。"""
    if not text:
        return []
    seen = []
    for m in MENTION_REGEX.finditer(text):
        name = m.group(2)
        if name not in seen:
            seen.append(name)
    return seen
