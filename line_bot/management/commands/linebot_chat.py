"""LINE接続なしでボットと対話するCLIモード。

使い方:
    python manage.py linebot_chat
    python manage.py linebot_chat --user dummy-001
    python manage.py linebot_chat --reset    # 対話履歴を初期化

LINE Developers の設定前でも、handlers.py のロジック確認が可能。
"""
from django.core.management.base import BaseCommand

from line_bot import handlers
from line_bot.models import LineUser, LineMessage


DUMMY_USER_ID = 'CLI-DUMMY-USER'


class Command(BaseCommand):
    help = 'LINEボットとCLIで対話してロジックを確認する（接続不要）'

    def add_arguments(self, parser):
        parser.add_argument('--user', default=DUMMY_USER_ID,
                            help='対話に使うLINEユーザーID（テスト用）')
        parser.add_argument('--reset', action='store_true',
                            help='指定ユーザーの履歴を消してから開始')
        parser.add_argument('--follow', action='store_true',
                            help='開始時に friend追加 イベントを発火させる')

    def handle(self, *args, **options):
        user_id = options['user']

        if options['reset']:
            LineMessage.objects.filter(line_user__line_user_id=user_id).delete()
            LineUser.objects.filter(line_user_id=user_id).delete()
            self.stdout.write(self.style.WARNING(f'ユーザー {user_id} をリセットしました'))

        self.stdout.write(self.style.SUCCESS(
            '\n=== げんばカルテ LINEボット ダミーモード ===\n'
            f'ユーザーID: {user_id}\n'
            '終了するには /quit または Ctrl+C\n'
            'コマンド: /follow=友だち追加, /unfollow=ブロック, /history=履歴表示\n'
        ))

        if options['follow']:
            self._dispatch_follow(user_id)

        try:
            while True:
                try:
                    text = input('あなた> ').strip()
                except EOFError:
                    break
                if not text:
                    continue
                if text in ('/quit', '/exit'):
                    break
                if text == '/follow':
                    self._dispatch_follow(user_id)
                    continue
                if text == '/unfollow':
                    handlers.handle_unfollow(user_id)
                    self.stdout.write(self.style.WARNING('[ブロック扱いにしました]'))
                    continue
                if text == '/history':
                    self._show_history(user_id)
                    continue

                result = handlers.handle_message(user_id, text)
                for reply in result.replies:
                    self._print_bot(reply)
        except KeyboardInterrupt:
            pass

        self.stdout.write('\n終了しました。')

    def _dispatch_follow(self, user_id: str) -> None:
        result = handlers.handle_follow(user_id)
        for reply in result.replies:
            self._print_bot(reply)

    def _print_bot(self, text: str) -> None:
        self.stdout.write(self.style.SUCCESS('ボット> ') + text.replace('\n', '\n        '))

    def _show_history(self, user_id: str) -> None:
        msgs = LineMessage.objects.filter(
            line_user__line_user_id=user_id
        ).order_by('created_at')[:50]
        for m in msgs:
            tag = '受' if m.direction == 'in' else '送'
            self.stdout.write(f'[{tag}] {m.text[:80]}')
