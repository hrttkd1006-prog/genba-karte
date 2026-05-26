"""LINE Messaging API Webhook 受信ビュー。"""
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import handlers
from .services import get_webhook_parser, reply_texts

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook(request: HttpRequest) -> HttpResponse:
    signature = request.headers.get('X-Line-Signature', '')
    body = request.body.decode('utf-8')

    if not settings.LINE_CHANNEL_SECRET or not settings.LINE_CHANNEL_ACCESS_TOKEN:
        logger.error('LINE channel credentials are not configured.')
        return HttpResponse(status=503)

    try:
        from linebot.v3.exceptions import InvalidSignatureError
    except ImportError:
        logger.exception('line-bot-sdk is not installed.')
        return HttpResponse(status=503)

    parser = get_webhook_parser()
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        logger.warning('Invalid LINE signature.')
        return HttpResponseBadRequest('Invalid signature')

    for event in events:
        try:
            _dispatch(event)
        except Exception:
            logger.exception('Failed to handle LINE event: %r', event)

    return HttpResponse('OK')


def _dispatch(event) -> None:
    event_type = getattr(event, 'type', None) or event.__class__.__name__.lower()
    line_user_id = event.source.user_id
    raw = _event_to_dict(event)

    if 'message' in event_type:
        text = getattr(event.message, 'text', '') or ''
        result = handlers.handle_message(
            line_user_id, text,
            message_type=event.message.type, raw_event=raw,
        )
        if result.replies:
            reply_texts(event.reply_token, result.replies)
    elif 'unfollow' in event_type:
        handlers.handle_unfollow(line_user_id, raw_event=raw)
    elif 'follow' in event_type:
        result = handlers.handle_follow(line_user_id, raw_event=raw)
        if result.replies:
            reply_texts(event.reply_token, result.replies)
    else:
        logger.info('Unhandled LINE event type: %s', event_type)


def _event_to_dict(event) -> dict:
    try:
        return event.to_dict()
    except Exception:
        return {'repr': repr(event)}
