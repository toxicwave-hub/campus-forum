"""轻量级 OpenGraph 链接预览抓取，使用标准库，不引入新依赖。"""
import re
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.utils import timezone

from .models import LinkPreview


URL_REGEX = re.compile(
    r'(?<!["\'\(])(https?://[^\s<>"\']+)',
    flags=re.IGNORECASE,
)


class _OGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.title = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self._in_title = True
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name') or ''
            value = attrs.get('content') or ''
            if key and value:
                self.meta[key.lower()] = value

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()


def _fetch_html(url, *, timeout=4):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; CampusForumBot/1.0)',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    with urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get('Content-Type', '')
        if 'text/html' not in ctype.lower():
            return ''
        raw = resp.read(512 * 1024)
    charset = 'utf-8'
    m = re.search(rb'charset="?([\w-]+)"?', raw, flags=re.IGNORECASE)
    if m:
        try:
            charset = m.group(1).decode('ascii')
        except Exception:
            pass
    try:
        return raw.decode(charset, errors='ignore')
    except Exception:
        return raw.decode('utf-8', errors='ignore')


def get_or_fetch_preview(url, *, max_age_hours=24 * 7):
    """读缓存或抓取一次。返回 LinkPreview 或 None。"""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return None

    obj = LinkPreview.objects.filter(url=url).first()
    if obj and obj.fetched_at >= timezone.now() - timedelta(hours=max_age_hours):
        return obj if obj.title or obj.description else None

    title = description = image = site_name = ''
    try:
        html = _fetch_html(url)
        if html:
            parser = _OGParser()
            parser.feed(html)
            meta = parser.meta
            title = meta.get('og:title') or parser.title or ''
            description = meta.get('og:description') or meta.get('description') or ''
            image = meta.get('og:image') or ''
            site_name = meta.get('og:site_name') or parsed.netloc
    except Exception:
        pass

    title = (title or '').strip()[:300]
    description = (description or '').strip()[:1000]
    image = (image or '').strip()[:500]
    site_name = (site_name or parsed.netloc).strip()[:100]

    if obj:
        obj.title = title
        obj.description = description
        obj.image = image
        obj.site_name = site_name
        obj.save()
    else:
        obj = LinkPreview.objects.create(
            url=url,
            title=title,
            description=description,
            image=image,
            site_name=site_name,
        )

    return obj if (title or description) else None


def extract_first_url(text):
    if not text:
        return None
    m = URL_REGEX.search(text)
    return m.group(1) if m else None
