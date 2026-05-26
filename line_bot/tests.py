"""line_bot のロジックテスト。

LINE SDK や外部通信なしで動く範囲をカバーする。
署名検証など SDK 必須の部分は実機検証フェーズに回す。
"""
from django.test import TestCase

from .faq import match_faq
from .handlers import handle_follow, handle_message
from .models import ConversationState, LineInquiry, LineMessage, LineUser
from .notifications import (
    announcement_message,
    new_job_message,
    new_review_message,
    send_to_followers,
)


TEST_USER = 'U-test-001'


class FaqMatchTests(TestCase):
    def test_matches_review_keyword(self):
        self.assertIn('レビュー', match_faq('レビュー見たい'))

    def test_matches_specific_before_general(self):
        # 「レビュー投稿」が「レビュー」より優先される
        reply = match_faq('レビュー投稿したい')
        self.assertIn('レビューを書く', reply)

    def test_no_match_returns_none(self):
        self.assertIsNone(match_faq('こんにちは'))

    def test_empty_text_returns_none(self):
        self.assertIsNone(match_faq(''))


class HandleFollowTests(TestCase):
    def test_creates_user_and_returns_welcome(self):
        result = handle_follow(TEST_USER)
        self.assertTrue(LineUser.objects.filter(line_user_id=TEST_USER).exists())
        self.assertEqual(len(result.replies), 1)
        self.assertIn('ようこそ', result.replies[0])

    def test_re_follow_updates_state(self):
        LineUser.objects.create(line_user_id=TEST_USER, is_followed=False)
        handle_follow(TEST_USER)
        self.assertTrue(LineUser.objects.get(line_user_id=TEST_USER).is_followed)


class HandleMessageTests(TestCase):
    def test_faq_match_returns_reply(self):
        result = handle_message(TEST_USER, '求人探したい')
        self.assertTrue(any('求人' in r for r in result.replies))

    def test_default_reply_when_no_match(self):
        result = handle_message(TEST_USER, 'なんでもいい話')
        self.assertEqual(len(result.replies), 1)
        self.assertIn('理解できない', result.replies[0])

    def test_messages_logged(self):
        handle_message(TEST_USER, '使い方教えて')
        msgs = LineMessage.objects.filter(line_user__line_user_id=TEST_USER)
        self.assertEqual(msgs.filter(direction='in').count(), 1)
        self.assertEqual(msgs.filter(direction='out').count(), 1)


class JobTransferFlowTests(TestCase):
    def setUp(self):
        self.user = LineUser.objects.create(line_user_id=TEST_USER)

    def _send(self, text):
        return handle_message(TEST_USER, text)

    def test_full_flow(self):
        # 開始
        r = self._send('転職したい')
        self.assertTrue(any('エリア' in s for s in r.replies))
        self.assertEqual(ConversationState.objects.get(line_user=self.user).step, 1)

        # Q1: エリア
        r = self._send('4')  # 近畿
        self.assertTrue(any('施設' in s for s in r.replies))
        state = ConversationState.objects.get(line_user=self.user)
        self.assertEqual(state.data['area'], '近畿')

        # Q2: 施設
        r = self._send('クリニック')
        self.assertTrue(any('働き方' in s for s in r.replies))
        state.refresh_from_db()
        self.assertEqual(state.data['facility'], 'クリニック')

        # Q3: 働き方 → 終了
        r = self._send('1')  # 常勤
        self.assertFalse(ConversationState.objects.filter(line_user=self.user).exists())
        self.assertTrue(any('近畿' in s for s in r.replies))
        self.assertTrue(any('おすすめ' in s for s in r.replies))

    def test_invalid_choice_reasks(self):
        self._send('転職')
        r = self._send('火星')
        self.assertTrue(any('番号' in s for s in r.replies))
        # ステップは進まない
        self.assertEqual(
            ConversationState.objects.get(line_user=self.user).step, 1,
        )

    def test_cancel_aborts(self):
        self._send('転職')
        r = self._send('キャンセル')
        self.assertFalse(ConversationState.objects.filter(line_user=self.user).exists())
        self.assertTrue(any('キャンセル' in s for s in r.replies))


class InquiryFlowTests(TestCase):
    def test_creates_inquiry(self):
        handle_message(TEST_USER, '問い合わせしたい')
        handle_message(TEST_USER, 'パスワードリセットメールが届きません。確認お願いします。')
        self.assertEqual(LineInquiry.objects.count(), 1)
        inq = LineInquiry.objects.first()
        self.assertIn('パスワード', inq.body)
        self.assertEqual(inq.status, 'new')

    def test_too_short_body_reasks(self):
        handle_message(TEST_USER, '問い合わせ')
        r = handle_message(TEST_USER, 'やあ')
        self.assertEqual(LineInquiry.objects.count(), 0)
        self.assertTrue(any('詳しく' in s for s in r.replies))


class NotificationTemplateTests(TestCase):
    def test_review_template(self):
        msg = new_review_message(
            hospital_name='テスト病院', rating=4.0,
            snippet='働きやすい職場でした', hospital_url='https://example.com/h/1',
        )
        self.assertIn('テスト病院', msg)
        self.assertIn('★★★★', msg)

    def test_job_template(self):
        msg = new_job_message(
            hospital_name='X病院', title='臨床検査技師募集',
            employment_type='常勤', job_url='https://example.com/j/1',
        )
        self.assertIn('X病院', msg)
        self.assertIn('臨床検査技師募集', msg)

    def test_announcement_with_url(self):
        msg = announcement_message(title='メンテ', body='本文', url='https://x')
        self.assertIn('メンテ', msg)
        self.assertIn('https://x', msg)


class BroadcastDryRunTests(TestCase):
    def test_dry_run_logs_to_db(self):
        LineUser.objects.create(line_user_id='U1', is_followed=True)
        LineUser.objects.create(line_user_id='U2', is_followed=True)
        LineUser.objects.create(line_user_id='U3', is_followed=False)
        count = send_to_followers('test message', dry_run=True)
        self.assertEqual(count, 2)
        self.assertEqual(LineMessage.objects.filter(message_type='push_dry').count(), 2)
