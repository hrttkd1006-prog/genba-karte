"""LINEイベントごとの処理。

設計方針:
- ハンドラは「送信内容（テキストのリスト）」を返すだけ。
- 実際の送信は views.py（本番）/ management command（ダミーモード）が行う。
- これにより LINE 接続なしでもロジックを完全にテスト可能。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

from .models import LineUser, LineMessage


WELCOME_TEXT = (
    'げんばカルテ公式LINEへようこそ！\n'
    '気になることをメッセージで送ってください。\n\n'
    '【できること】\n'
    '・「レビュー」でレビュー一覧\n'
    '・「求人」で求人検索\n'
    '・「転職」で転職相談\n'
    '・「使い方」で使い方ガイド\n'
    '・「問い合わせ」で運営への連絡'
)

DEFAULT_REPLY = (
    'すみません、まだ理解できないメッセージでした。\n'
    '「レビュー」「求人」「転職」「使い方」「問い合わせ」と送ってみてください。'
)


@dataclass
class HandlerResult:
    """ハンドラの実行結果。"""
    replies: list[str] = field(default_factory=list)
    line_user: Optional[LineUser] = None

    def add(self, text: str) -> 'HandlerResult':
        self.replies.append(text)
        return self


def handle_follow(line_user_id: str, raw_event: dict | None = None) -> HandlerResult:
    """友だち追加。"""
    user, _ = LineUser.objects.update_or_create(
        line_user_id=line_user_id,
        defaults={'is_followed': True, 'unfollowed_at': None},
    )
    LineMessage.objects.create(
        line_user=user, direction='in', message_type='follow', raw_event=raw_event,
    )
    return _record_replies(user, HandlerResult(line_user=user).add(WELCOME_TEXT))


def handle_unfollow(line_user_id: str, raw_event: dict | None = None) -> HandlerResult:
    """ブロック・友だち解除。返信なし。"""
    LineUser.objects.filter(line_user_id=line_user_id).update(
        is_followed=False, unfollowed_at=timezone.now(),
    )
    return HandlerResult()


def handle_message(line_user_id: str, text: str, message_type: str = 'text',
                   raw_event: dict | None = None) -> HandlerResult:
    """テキストメッセージ受信。"""
    from .faq import match_faq

    user, _ = LineUser.objects.get_or_create(line_user_id=line_user_id)
    LineMessage.objects.create(
        line_user=user, direction='in', message_type=message_type,
        text=text, raw_event=raw_event,
    )

    result = HandlerResult(line_user=user)

    # 1. 会話フロー進行中なら最優先
    from .flows import advance_active_flow
    flow_reply = advance_active_flow(user, text)
    if flow_reply is not None:
        for r in flow_reply:
            result.add(r)
        return _record_replies(user, result)

    # 2. FAQ マッチ
    faq_reply = match_faq(text)
    if faq_reply:
        result.add(faq_reply)
        return _record_replies(user, result)

    # 3. デフォルト
    result.add(DEFAULT_REPLY)
    return _record_replies(user, result)


def _record_replies(user: LineUser, result: HandlerResult) -> HandlerResult:
    """送信メッセージをログに残す。"""
    for r in result.replies:
        LineMessage.objects.create(
            line_user=user, direction='out', message_type='text', text=r,
        )
    return result
