import json
import re
import anthropic
from django.conf import settings


def moderate_review(review_text: str, ip_address: str = None) -> dict:
    """
    Claude APIでレビューを審査する。
    Returns: {"judgment": "white"|"gray"|"black", "reason": str}
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""以下は臨床検査技師の職場レビューサイトへの投稿です。投稿内容を審査してください。

【投稿内容】
{review_text}

【審査基準】
- black（自動非公開）: 特定個人名が含まれる、明らかな暴言・罵倒・侮辱表現、スパム・無意味な投稿（10文字以下等）
- gray（管理者確認）: 誇張表現（「最悪」「死ぬほど」等）、強い感情表現が含まれる
- white（即時公開）: 上記に該当しない、事実や意見に基づく記述

JSONのみで回答してください（他のテキスト不要）:
{{"judgment": "black" | "gray" | "white", "reason": "判定理由を日本語で簡潔に"}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        # JSON部分だけ抽出
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if result.get('judgment') in ('white', 'gray', 'black'):
                return result
    except Exception:
        pass

    # API失敗時はgrayにして管理者確認
    return {"judgment": "gray", "reason": "AI審査エラーのため管理者が確認します"}


def build_review_text(review) -> str:
    parts = []
    if review.good_points:
        parts.append(f"良かった点: {review.good_points}")
    if review.concerns:
        parts.append(f"気になった点: {review.concerns}")
    if review.suitable_for:
        parts.append(f"向いている人: {review.suitable_for}")
    return "\n".join(parts)
