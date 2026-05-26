"""プッシュ通知のテンプレと送信ロジック。

現状は LINE 接続前なので、send_to_followers は dry_run=True で
「送るはずの内容をログ出力するだけ」になる。

LINE 設定完了後に dry_run=False で呼ぶか、本番では既定で送信に切り替える。
"""
from __future__ import annotations

import logging
from typing import Iterable

from .models import LineUser, LineMessage

logger = logging.getLogger(__name__)

BASE_URL = 'https://genba-karte.com'


# ---- テンプレ生成 ----
def new_review_message(*, hospital_name: str, rating: float, snippet: str,
                       hospital_url: str) -> str:
    """新着レビュー通知。
    snippet は本文の冒頭抜粋（プライバシー配慮で短く）。
    """
    stars = '★' * int(round(rating)) + '☆' * (5 - int(round(rating)))
    return (
        f'📝 新着レビュー\n'
        f'【{hospital_name}】 {stars} ({rating:.1f})\n\n'
        f'{_truncate(snippet, 80)}\n\n'
        f'続きを読む 👉 {hospital_url}'
    )


def new_job_message(*, hospital_name: str, title: str, employment_type: str,
                    job_url: str) -> str:
    """新着求人通知。"""
    return (
        f'💼 新着求人\n'
        f'【{hospital_name}】\n'
        f'{title}（{employment_type}）\n\n'
        f'詳細・応募 👉 {job_url}'
    )


def announcement_message(*, title: str, body: str, url: str | None = None) -> str:
    """運営からのお知らせ。"""
    msg = f'📢 {title}\n\n{body}'
    if url:
        msg += f'\n\n👉 {url}'
    return msg


# ---- 送信 ----
def send_to_followers(text: str, *, dry_run: bool = True,
                      user_ids: Iterable[str] | None = None) -> int:
    """フォロワー全員（または指定ユーザー）にプッシュ送信。

    Args:
        text: 送信本文
        dry_run: True なら実送信せずログとDB保存のみ
        user_ids: 指定すると該当ユーザーだけに送る
    Returns:
        対象ユーザー数
    """
    qs = LineUser.objects.filter(is_followed=True)
    if user_ids is not None:
        qs = qs.filter(line_user_id__in=list(user_ids))

    count = 0
    for user in qs:
        count += 1
        if dry_run:
            logger.info('[DRY RUN] push to %s: %s', user.line_user_id, text[:50])
        else:
            try:
                from .services import push_text
                push_text(user.line_user_id, text)
            except Exception:
                logger.exception('Failed to push to %s', user.line_user_id)
                continue
        LineMessage.objects.create(
            line_user=user, direction='out',
            message_type='push_dry' if dry_run else 'push',
            text=text,
        )
    return count


def _truncate(text: str, length: int) -> str:
    text = (text or '').strip().replace('\n', ' ')
    if len(text) <= length:
        return text
    return text[:length] + '…'
