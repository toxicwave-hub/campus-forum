from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Message, Post, Reply, Report, UserProfile


class StyledFormMixin:
    default_class = 'form-input'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            existing = field.widget.attrs.get('class', '')
            css = f'{existing} {self.default_class}'.strip()
            field.widget.attrs['class'] = css
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label or name


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)] if data else []


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(label='邮箱', required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {'username': '用户名'}


class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class PostForm(StyledFormMixin, forms.ModelForm):
    attachments = MultipleFileField(
        label='附件（图片 / 视频 / 文件）', required=False
    )
    save_as_draft = forms.BooleanField(label='保存为草稿', required=False)

    class Meta:
        model = Post
        fields = ('title', 'content', 'cover_image', 'is_nsfw')
        labels = {
            'title': '标题',
            'content': '正文（支持 Markdown）',
            'cover_image': '封面图（可选）',
            'is_nsfw': '标记为 NSFW',
        }
        widgets = {'content': forms.Textarea(attrs={'rows': 12})}


class ReplyForm(StyledFormMixin, forms.ModelForm):
    attachments = MultipleFileField(label='附件', required=False)

    class Meta:
        model = Reply
        fields = ('content',)
        labels = {'content': '回复内容（支持 Markdown）'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': '写下你的回复'}),
        }


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('nickname', 'bio', 'avatar', 'avatar_color')
        labels = {
            'nickname': '昵称',
            'bio': '个人简介',
            'avatar': '头像图片（可选）',
            'avatar_color': '字母头像颜色（HEX）',
        }
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}


class SearchForm(StyledFormMixin, forms.Form):
    q = forms.CharField(label='搜索', required=False, max_length=100)


class MessageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Message
        fields = ('content', 'image')
        labels = {'content': '消息', 'image': '附图（可选）'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': '在这里输入消息…'}),
        }


class ReportForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Report
        fields = ('reason', 'detail')
        labels = {'reason': '原因', 'detail': '详细描述（可选）'}
        widgets = {'detail': forms.Textarea(attrs={'rows': 3})}
