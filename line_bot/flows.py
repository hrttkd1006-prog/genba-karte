"""多段会話フロー。

設計:
- 各フローは (start_keywords, run関数) を持つ
- run(state, text) → list[str]（次のメッセージ） を返す
- フロー終了時は state を削除
- 「キャンセル」「やめる」でいつでも中止可能
"""
from __future__ import annotations

from typing import Callable, Optional

from .models import LineUser, ConversationState, LineInquiry


CANCEL_KEYWORDS = ('キャンセル', 'やめる', 'やめて', '中止', '/cancel')


# ---- フロー登録 ----
_FLOW_REGISTRY: dict[str, 'Flow'] = {}


class Flow:
    def __init__(self, name: str, start_keywords: tuple[str, ...],
                 run: Callable[[ConversationState, str], list[str]]):
        self.name = name
        self.start_keywords = start_keywords
        self.run = run


def register(flow: Flow) -> None:
    _FLOW_REGISTRY[flow.name] = flow


def _find_starter(text: str) -> Optional['Flow']:
    for flow in _FLOW_REGISTRY.values():
        for kw in flow.start_keywords:
            if kw in text:
                return flow
    return None


# ---- 公開エントリーポイント ----
def advance_active_flow(user: LineUser, text: str) -> list[str] | None:
    """進行中フローがあれば1ステップ進める。新規開始ワードならフロー開始。
    何もなければ None。
    """
    # キャンセル処理
    if any(kw in text for kw in CANCEL_KEYWORDS):
        deleted, _ = ConversationState.objects.filter(line_user=user).delete()
        if deleted:
            return ['会話をキャンセルしました。「転職」「問い合わせ」などで再開できます。']
        return None

    # 既存フロー進行中？
    state = ConversationState.objects.filter(line_user=user).first()
    if state:
        flow = _FLOW_REGISTRY.get(state.flow_name)
        if flow:
            return flow.run(state, text)
        # 不明なフロー名なら掃除
        state.delete()

    # 新規開始
    starter = _find_starter(text)
    if starter:
        state = ConversationState.objects.create(
            line_user=user, flow_name=starter.name, step=0, data={},
        )
        return starter.run(state, text)

    return None


# ---- 転職誘導フロー ----
JOB_AREAS = ('北海道・東北', '関東', '中部', '近畿', '中国・四国', '九州・沖縄', 'こだわらない')
JOB_FACILITY_TYPES = ('総合病院', '大学病院', 'クリニック', '検査センター', 'こだわらない')
JOB_WORKSTYLES = ('常勤', '非常勤・パート', '派遣', 'こだわらない')


def _job_transfer_flow(state: ConversationState, text: str) -> list[str]:
    step = state.step

    if step == 0:
        state.step = 1
        state.save(update_fields=['step', 'updated_at'])
        return [
            '転職相談ですね！数問お伺いします（途中で「キャンセル」と送れば中断できます）。\n\n'
            'Q1. 希望勤務エリアを番号で教えてください。\n'
            + _numbered(JOB_AREAS)
        ]

    if step == 1:
        choice = _parse_choice(text, JOB_AREAS)
        if choice is None:
            return ['番号（1〜{}）または選択肢の名前で答えてください。\n\n'.format(len(JOB_AREAS))
                    + _numbered(JOB_AREAS)]
        state.data['area'] = choice
        state.step = 2
        state.save(update_fields=['data', 'step', 'updated_at'])
        return [
            f'「{choice}」ですね。\n\n'
            'Q2. 希望の施設タイプは？\n'
            + _numbered(JOB_FACILITY_TYPES)
        ]

    if step == 2:
        choice = _parse_choice(text, JOB_FACILITY_TYPES)
        if choice is None:
            return ['番号または名前で答えてください。\n\n' + _numbered(JOB_FACILITY_TYPES)]
        state.data['facility'] = choice
        state.step = 3
        state.save(update_fields=['data', 'step', 'updated_at'])
        return [
            f'「{choice}」ですね。\n\n'
            'Q3. 希望の働き方は？\n'
            + _numbered(JOB_WORKSTYLES)
        ]

    if step == 3:
        choice = _parse_choice(text, JOB_WORKSTYLES)
        if choice is None:
            return ['番号または名前で答えてください。\n\n' + _numbered(JOB_WORKSTYLES)]
        state.data['workstyle'] = choice

        summary = (
            'ありがとうございます！以下の希望でお探しします。\n'
            f'・エリア: {state.data["area"]}\n'
            f'・施設: {state.data["facility"]}\n'
            f'・働き方: {state.data["workstyle"]}'
        )
        recommendations = _build_recommendations(state.data)
        state.delete()
        return [summary, recommendations]

    # 想定外
    state.delete()
    return ['会話をリセットしました。「転職」と送ると再開できます。']


def _numbered(items: tuple[str, ...]) -> str:
    return '\n'.join(f'{i+1}. {v}' for i, v in enumerate(items))


def _parse_choice(text: str, items: tuple[str, ...]) -> str | None:
    t = text.strip()
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(items):
            return items[idx]
    for v in items:
        if v in t or t in v:
            return v
    return None


def _build_recommendations(data: dict) -> str:
    """希望条件からおすすめリンクを組み立て（仮）。
    medical_affiliate との連携や実際のアフィリエイトURLは後で差し替え。
    """
    return (
        '【おすすめ求人・エージェント】\n'
        '👉 げんばカルテの求人検索: https://genba-karte.com/jobs/\n'
        '👉 提携エージェントに無料相談（実装予定）\n\n'
        'より詳しいご希望は「問い合わせ」と送って運営にメッセージしてください。'
    )


register(Flow(
    name='job_transfer',
    start_keywords=('転職', '求人相談', 'エージェント'),
    run=_job_transfer_flow,
))


# ---- 問い合わせフロー ----
INQUIRY_MIN_LENGTH = 5
INQUIRY_MAX_LENGTH = 1000


def _inquiry_flow(state: ConversationState, text: str) -> list[str]:
    step = state.step

    if step == 0:
        state.step = 1
        state.save(update_fields=['step', 'updated_at'])
        return [
            '運営へのお問い合わせを受け付けます。\n'
            '内容を1つのメッセージにまとめて送ってください。\n'
            '（途中でやめる場合は「キャンセル」と送信）'
        ]

    if step == 1:
        body = text.strip()
        if len(body) < INQUIRY_MIN_LENGTH:
            return [f'もう少し詳しく書いていただけますか？（{INQUIRY_MIN_LENGTH}文字以上）']
        if len(body) > INQUIRY_MAX_LENGTH:
            return [f'長すぎます。{INQUIRY_MAX_LENGTH}文字以内でお願いします。']

        LineInquiry.objects.create(line_user=state.line_user, body=body)
        state.delete()
        return [
            'お問い合わせを受け付けました。ありがとうございます。\n'
            '内容を確認のうえ、必要に応じて運営からご返信します。'
        ]

    state.delete()
    return ['会話をリセットしました。']


register(Flow(
    name='inquiry',
    start_keywords=('問い合わせ', 'お問い合わせ', '質問したい', '相談したい', 'クレーム'),
    run=_inquiry_flow,
))
