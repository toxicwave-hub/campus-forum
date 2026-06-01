import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import (
    Attachment, Board, Bookmark, Notification, Post, PostVote, Reply, ReplyVote,
)


def make_image_bytes():
    """生成一个 1x1 的 PNG。"""
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (1, 1), (255, 0, 0)).save(buf, format='PNG')
    return buf.getvalue()


class ForumBaseTestCase(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='Pwd-12345!')
        self.bob = User.objects.create_user('bob', password='Pwd-12345!')
        self.board = Board.objects.create(
            name='测试板块', slug='test-board', description='for tests'
        )

    def login(self, user):
        self.client.force_login(user)


class HomeAndNavigationTests(ForumBaseTestCase):
    def test_home_page_renders(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'CYBER')

    def test_board_detail_renders(self):
        resp = self.client.get(reverse('board_detail', args=[self.board.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.board.name)


class AccountFlowTests(TestCase):
    def test_register_normalizes_username_and_logs_user_in(self):
        response = self.client.post(reverse('register'), {
            'username': 'NewStudent',
            'email': 'new@example.com',
            'password1': 'Pwd-12345!',
            'password2': 'Pwd-12345!',
        })
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='newstudent')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_login_username_is_case_insensitive(self):
        User.objects.create_user('mixedcase', password='Pwd-12345!')
        response = self.client.post(reverse('login'), {
            'username': 'MixedCase',
            'password': 'Pwd-12345!',
        })
        self.assertRedirects(response, reverse('home'))

    def test_register_rejects_case_insensitive_duplicate(self):
        User.objects.create_user('existing', password='Pwd-12345!')
        response = self.client.post(reverse('register'), {
            'username': 'Existing',
            'password1': 'Pwd-12345!',
            'password2': 'Pwd-12345!',
        })
        self.assertContains(response, '这个用户名已经被注册。')


class PostFlowTests(ForumBaseTestCase):
    def test_post_create_requires_login(self):
        url = reverse('new_post', args=[self.board.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp['Location'])

    def test_post_create_and_detail(self):
        self.login(self.alice)
        url = reverse('new_post', args=[self.board.slug])
        resp = self.client.post(url, {'title': '你好', 'content': '正文'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        post = Post.objects.get(title='你好')
        self.assertEqual(post.author, self.alice)
        self.assertContains(resp, '你好')

    def test_post_edit_only_by_author(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        resp = self.client.get(reverse('post_edit', args=[post.pk]))
        self.assertEqual(resp.status_code, 403)

        self.login(self.alice)
        self.client.post(
            reverse('post_edit', args=[post.pk]),
            {'title': 't2', 'content': 'c2'},
            follow=True,
        )
        post.refresh_from_db()
        self.assertEqual(post.title, 't2')

    def test_post_delete_only_by_author(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        resp = self.client.post(reverse('post_delete', args=[post.pk]))
        self.assertEqual(resp.status_code, 403)
        self.login(self.alice)
        self.client.post(reverse('post_delete', args=[post.pk]))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())


class ReplyFlowTests(ForumBaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )

    def test_reply_creates_notification_to_post_author(self):
        self.login(self.bob)
        self.client.post(
            reverse('post_detail', args=[self.post.pk]), {'content': 'hi'}
        )
        self.assertEqual(Reply.objects.count(), 1)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.alice, kind=Notification.KIND_REPLY
            ).count(),
            1,
        )

    def test_self_reply_does_not_create_notification(self):
        self.login(self.alice)
        self.client.post(
            reverse('post_detail', args=[self.post.pk]), {'content': 'self'}
        )
        self.assertEqual(Notification.objects.count(), 0)

    def test_nested_reply_notifies_parent_author(self):
        parent = Reply.objects.create(post=self.post, author=self.bob, content='p')
        carol = User.objects.create_user('carol', password='Pwd-12345!')
        self.client.force_login(carol)
        self.client.post(
            reverse('post_detail', args=[self.post.pk]),
            {'content': 'child', 'parent': parent.pk},
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.bob, kind=Notification.KIND_REPLY_TO_REPLY
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.alice, kind=Notification.KIND_REPLY
            ).exists()
        )


class VotingTests(ForumBaseTestCase):
    def test_vote_post_up_then_change_to_down(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        self.client.post(reverse('post_vote', args=[post.pk]), {'value': '1'})
        post.refresh_from_db()
        self.assertEqual(post.score, 1)
        self.assertEqual(PostVote.objects.count(), 1)

        # 改投反对
        self.client.post(reverse('post_vote', args=[post.pk]), {'value': '-1'})
        post.refresh_from_db()
        self.assertEqual(post.score, -1)
        self.assertEqual(PostVote.objects.count(), 1)

        # 取消
        self.client.post(reverse('post_vote', args=[post.pk]), {'value': '0'})
        post.refresh_from_db()
        self.assertEqual(post.score, 0)
        self.assertEqual(PostVote.objects.count(), 0)

    def test_upvote_post_creates_notification(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        self.client.post(reverse('post_vote', args=[post.pk]), {'value': '1'})
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.alice, kind=Notification.KIND_POST_LIKE
            ).exists()
        )

    def test_downvote_does_not_notify(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        self.client.post(reverse('post_vote', args=[post.pk]), {'value': '-1'})
        self.assertFalse(
            Notification.objects.filter(recipient=self.alice).exists()
        )

    def test_vote_reply(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        reply = Reply.objects.create(post=post, author=self.alice, content='r')
        self.login(self.bob)
        self.client.post(reverse('reply_vote', args=[reply.pk]), {'value': '1'})
        reply.refresh_from_db()
        self.assertEqual(reply.score, 1)
        self.assertEqual(ReplyVote.objects.count(), 1)


class BookmarkTests(ForumBaseTestCase):
    def test_toggle_bookmark(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        self.client.post(reverse('toggle_bookmark', args=[post.pk]))
        self.assertEqual(Bookmark.objects.count(), 1)
        self.client.post(reverse('toggle_bookmark', args=[post.pk]))
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_bookmark_list_only_shows_own(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='独特标题ABC', content='c'
        )
        Bookmark.objects.create(user=self.bob, post=post)
        self.login(self.alice)
        resp = self.client.get(reverse('bookmarks'))
        self.assertNotContains(resp, '独特标题ABC')

        self.login(self.bob)
        resp = self.client.get(reverse('bookmarks'))
        self.assertContains(resp, '独特标题ABC')


@override_settings(MEDIA_ROOT='/tmp/campus-forum-test-media')
class AttachmentTests(ForumBaseTestCase):
    def test_create_post_with_image_attachment(self):
        self.login(self.alice)
        img = SimpleUploadedFile('hi.png', make_image_bytes(), content_type='image/png')
        resp = self.client.post(
            reverse('new_post', args=[self.board.slug]),
            {'title': '带图', 'content': '正文', 'attachments': img},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        att = Attachment.objects.first()
        self.assertIsNotNone(att)
        self.assertEqual(att.kind, Attachment.KIND_IMAGE)
        self.assertEqual(att.uploader, self.alice)
        self.assertGreater(att.size, 0)

    def test_unknown_extension_rejected(self):
        from django.core.exceptions import ValidationError
        from .uploads import detect_kind
        with self.assertRaises(ValidationError):
            detect_kind('virus.exe')


class MentionTests(ForumBaseTestCase):
    def test_mention_creates_notification(self):
        self.login(self.alice)
        self.client.post(
            reverse('new_post', args=[self.board.slug]),
            {'title': 't', 'content': '提到 @bob 看看'},
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.bob, kind=Notification.KIND_MENTION
            ).exists()
        )

    def test_mention_self_no_notification(self):
        self.login(self.alice)
        self.client.post(
            reverse('new_post', args=[self.board.slug]),
            {'title': 't', 'content': '我 @alice 自己'},
        )
        self.assertFalse(
            Notification.objects.filter(recipient=self.alice).exists()
        )


class SearchTests(ForumBaseTestCase):
    def test_search_finds_post_by_title_and_content(self):
        Post.objects.create(
            board=self.board, author=self.alice, title='Django 教程', content='正文'
        )
        Post.objects.create(
            board=self.board, author=self.alice, title='React', content='提到 Django'
        )
        resp = self.client.get(reverse('search'), {'q': 'Django'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Django 教程')
        self.assertContains(resp, 'React')


class ViewCountTests(ForumBaseTestCase):
    def test_view_count_dedup_per_session(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        client = Client()
        client.get(reverse('post_detail', args=[post.pk]))
        client.get(reverse('post_detail', args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual(post.view_count, 1)


class ProfileEditTests(ForumBaseTestCase):
    def test_profile_edit_updates_nickname(self):
        self.login(self.alice)
        resp = self.client.post(
            reverse('profile_edit'),
            {'nickname': '艾丽丝', 'bio': '你好', 'avatar_color': '#dc2626'},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.nickname, '艾丽丝')


class MarkdownTests(TestCase):
    def test_markdown_renders_and_sanitizes(self):
        from .markdown_utils import render_markdown
        html = render_markdown('**bold** <script>alert(1)</script>')
        self.assertIn('<strong>bold</strong>', html)
        self.assertNotIn('<script>', html)

    def test_markdown_renders_code_block(self):
        from .markdown_utils import render_markdown
        html = render_markdown('```python\nprint("hi")\n```')
        self.assertIn('codehilite', html)

    def test_extract_mentions(self):
        from .markdown_utils import extract_mentions
        names = extract_mentions('hello @alice and @bob and @alice again')
        self.assertEqual(names, ['alice', 'bob'])


class HotScoreTests(TestCase):
    def test_hot_score_monotonic_with_score(self):
        from django.utils import timezone
        from .voting import hot_score
        now = timezone.now()
        self.assertGreater(hot_score(100, now), hot_score(10, now))
        self.assertGreater(hot_score(0, now), hot_score(-10, now))



class FollowTests(ForumBaseTestCase):
    def test_toggle_follow_and_notification(self):
        self.login(self.bob)
        resp = self.client.post(reverse('toggle_follow', args=[self.alice.username]))
        self.assertEqual(resp.status_code, 302)
        from .models import Follow
        self.assertEqual(Follow.objects.count(), 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.alice, kind=Notification.KIND_FOLLOW
            ).exists()
        )
        # 再点取消
        self.client.post(reverse('toggle_follow', args=[self.alice.username]))
        self.assertEqual(Follow.objects.count(), 0)

    def test_cannot_follow_self(self):
        self.login(self.alice)
        resp = self.client.post(reverse('toggle_follow', args=[self.alice.username]))
        self.assertEqual(resp.status_code, 400)


class SubscribeTests(ForumBaseTestCase):
    def test_toggle_subscribe(self):
        from .models import BoardSubscription
        self.login(self.alice)
        self.client.post(reverse('toggle_subscribe', args=[self.board.slug]))
        self.assertEqual(BoardSubscription.objects.count(), 1)
        self.client.post(reverse('toggle_subscribe', args=[self.board.slug]))
        self.assertEqual(BoardSubscription.objects.count(), 0)

    def test_subscribed_feed(self):
        from .models import BoardSubscription
        other_board = Board.objects.create(name='Other', slug='other')
        Post.objects.create(
            board=self.board, author=self.alice, title='IN_FEED', content='c'
        )
        Post.objects.create(
            board=other_board, author=self.alice, title='NOT_IN_FEED', content='c'
        )
        BoardSubscription.objects.create(user=self.bob, board=self.board)
        self.login(self.bob)
        resp = self.client.get(reverse('home') + '?feed=subscribed')
        self.assertContains(resp, 'IN_FEED')
        self.assertNotContains(resp, 'NOT_IN_FEED')


class MessagingTests(ForumBaseTestCase):
    def test_send_message_creates_conversation(self):
        from .models import Conversation, Message
        self.login(self.alice)
        resp = self.client.post(
            reverse('conversation', args=[self.bob.username]),
            {'content': 'yo'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.bob, kind=Notification.KIND_MESSAGE
            ).exists()
        )

    def test_cannot_message_self(self):
        self.login(self.alice)
        resp = self.client.get(reverse('conversation', args=[self.alice.username]))
        self.assertEqual(resp.status_code, 302)


class DraftTests(ForumBaseTestCase):
    def test_save_as_draft(self):
        self.login(self.alice)
        self.client.post(
            reverse('new_post', args=[self.board.slug]),
            {'title': '草稿帖', 'content': 'c', 'save_as_draft': 'on'},
        )
        post = Post.objects.get(title='草稿帖')
        self.assertEqual(post.status, Post.STATUS_DRAFT)

    def test_draft_not_visible_to_others(self):
        post = Post.objects.create(
            board=self.board, author=self.alice, title='secret',
            content='c', status=Post.STATUS_DRAFT,
        )
        self.login(self.bob)
        resp = self.client.get(reverse('post_detail', args=[post.pk]))
        self.assertEqual(resp.status_code, 403)


class ReportTests(ForumBaseTestCase):
    def test_report_post(self):
        from .models import Report
        post = Post.objects.create(
            board=self.board, author=self.alice, title='t', content='c'
        )
        self.login(self.bob)
        self.client.post(
            reverse('report_post', args=[post.pk]),
            {'reason': '广告', 'detail': '满屏广告'},
        )
        self.assertEqual(Report.objects.count(), 1)


class ModeratorTests(ForumBaseTestCase):
    def test_moderator_can_remove_via_report(self):
        from .models import BoardModerator, Report
        BoardModerator.objects.create(board=self.board, user=self.bob)
        post = Post.objects.create(
            board=self.board, author=self.alice, title='spam', content='c'
        )
        report = Report.objects.create(
            reporter=self.alice, kind=Report.KIND_POST, post=post,
            reason='广告',
        )
        self.login(self.bob)
        resp = self.client.post(
            reverse('mod_report_resolve', args=[report.pk]),
            {'action': 'remove'},
        )
        self.assertEqual(resp.status_code, 302)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.STATUS_REMOVED)


class UserSearchAPITests(ForumBaseTestCase):
    def test_user_search_returns_matches(self):
        self.login(self.alice)
        User.objects.create_user('alex', password='Pwd-12345!')
        resp = self.client.get(reverse('user_search_api') + '?q=al')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [r['username'] for r in data['results']]
        self.assertIn('alex', names)
        self.assertNotIn('alice', names)  # 排除自己
