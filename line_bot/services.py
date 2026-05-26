"""LINE Messaging API クライアントラッパー。

line-bot-sdk v3 を想定。SDK未インストール環境でも import エラーにならないよう
遅延インポートしている。
"""
from django.conf import settings


def get_messaging_api():
    """設定済みの MessagingApi インスタンスを返す。"""
    from linebot.v3.messaging import Configuration, ApiClient, MessagingApi

    config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    api_client = ApiClient(config)
    return MessagingApi(api_client)


def get_webhook_parser():
    """署名検証 + イベントパース用の WebhookParser を返す。"""
    from linebot.v3.webhook import WebhookParser
    return WebhookParser(settings.LINE_CHANNEL_SECRET)


def reply_text(reply_token: str, text: str) -> None:
    """指定 reply_token にテキスト1件を返信。"""
    reply_texts(reply_token, [text])


def reply_texts(reply_token: str, texts: list[str]) -> None:
    """指定 reply_token に複数テキストを返信（最大5件）。"""
    from linebot.v3.messaging import ReplyMessageRequest, TextMessage

    if not texts:
        return
    api = get_messaging_api()
    api.reply_message_with_http_info(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=t) for t in texts[:5]],
        )
    )


def push_text(line_user_id: str, text: str) -> None:
    """指定ユーザーにプッシュ送信。プッシュ通知機能の土台。"""
    from linebot.v3.messaging import PushMessageRequest, TextMessage

    api = get_messaging_api()
    api.push_message_with_http_info(
        PushMessageRequest(
            to=line_user_id,
            messages=[TextMessage(text=text)],
        )
    )
