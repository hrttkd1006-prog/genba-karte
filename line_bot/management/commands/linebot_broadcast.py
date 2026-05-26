"""フォロワーへの一斉プッシュ送信コマンド。

使い方:
    # ドライラン（本当に送らずログ出力）
    python manage.py linebot_broadcast --title "メンテナンス" --body "本日23時から〜"

    # 実送信（LINE設定完了後）
    python manage.py linebot_broadcast --title "..." --body "..." --send

    # 標準入力からテキストを受け取る
    echo "お知らせ本文" | python manage.py linebot_broadcast --title "お知らせ"
"""
import sys

from django.core.management.base import BaseCommand

from line_bot.notifications import announcement_message, send_to_followers


class Command(BaseCommand):
    help = 'LINE友だちに一斉プッシュ通知を送る（既定はドライラン）'

    def add_arguments(self, parser):
        parser.add_argument('--title', required=True, help='お知らせタイトル')
        parser.add_argument('--body', default=None, help='本文（未指定なら標準入力）')
        parser.add_argument('--url', default=None, help='リンク先URL')
        parser.add_argument('--send', action='store_true',
                            help='実際に送信する（指定しない場合はドライラン）')

    def handle(self, *args, **options):
        body = options['body']
        if body is None:
            body = sys.stdin.read().strip()
        if not body:
            self.stderr.write('本文が空です。--body または標準入力で指定してください。')
            return

        text = announcement_message(title=options['title'], body=body, url=options['url'])
        self.stdout.write('--- 送信プレビュー ---')
        self.stdout.write(text)
        self.stdout.write('----------------------')

        dry_run = not options['send']
        count = send_to_followers(text, dry_run=dry_run)
        mode = 'DRY RUN' if dry_run else '実送信'
        self.stdout.write(self.style.SUCCESS(f'[{mode}] 対象 {count} 人'))
        if dry_run:
            self.stdout.write('本番送信するには --send を付けてください。')
