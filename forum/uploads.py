"""统一处理上传文件的类型判断、尺寸校验、图片元信息读取。"""
import os

from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Attachment


def detect_kind(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in settings.ALLOWED_IMAGE_EXTS:
        return Attachment.KIND_IMAGE, ext
    if ext in settings.ALLOWED_VIDEO_EXTS:
        return Attachment.KIND_VIDEO, ext
    if ext in settings.ALLOWED_FILE_EXTS:
        return Attachment.KIND_FILE, ext
    raise ValidationError(f'不支持的文件类型：{ext}')


def validate_size(uploaded_file):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f'文件超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制。'
        )


def read_image_dimensions(uploaded_file):
    try:
        from PIL import Image
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        w, h = img.size
        uploaded_file.seek(0)
        return w, h
    except Exception:
        return None, None


def create_attachment(uploaded_file, *, post=None, reply=None, uploader=None):
    validate_size(uploaded_file)
    kind, _ = detect_kind(uploaded_file.name)

    width = height = None
    if kind == Attachment.KIND_IMAGE:
        width, height = read_image_dimensions(uploaded_file)

    return Attachment.objects.create(
        post=post,
        reply=reply,
        uploader=uploader,
        kind=kind,
        file=uploaded_file,
        original_name=uploaded_file.name[:200],
        size=uploaded_file.size,
        width=width,
        height=height,
    )
