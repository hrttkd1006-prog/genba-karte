import subprocess
import re
from datetime import date
from django.core.management.base import BaseCommand
from panel.models import ServerLog


def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ''


class Command(BaseCommand):
    help = '毎日のサーバー統計を収集してDBに保存する'

    def handle(self, *args, **options):
        today = date.today()

        # SSH不正試行ブロック数（fail2ban）
        ssh_blocked = 0
        try:
            out = run("fail2ban-client status sshd 2>/dev/null")
            m = re.search(r'Total banned:\s+(\d+)', out)
            if m:
                ssh_blocked = int(m.group(1))
        except Exception:
            pass

        # Nginxエラー数（本日分）
        nginx_errors = 0
        try:
            today_str = today.strftime('%Y/%m/%d')
            out = run(f"grep '{today_str}' /var/log/nginx/error.log 2>/dev/null | wc -l")
            nginx_errors = int(out) if out.isdigit() else 0
        except Exception:
            pass

        # 総アクセス数（本日分）
        nginx_requests = 0
        try:
            today_str = today.strftime('%d/%b/%Y')
            out = run(f"grep '{today_str}' /var/log/nginx/access.log 2>/dev/null | wc -l")
            nginx_requests = int(out) if out.isdigit() else 0
        except Exception:
            pass

        # ディスク使用率
        disk_usage = ''
        try:
            out = run("df -h / | awk 'NR==2 {print $5}'")
            disk_usage = out
        except Exception:
            pass

        # メモリ使用率
        memory_usage = ''
        try:
            out = run("free | awk '/Mem:/ {printf \"%.0f%%\", $3/$2*100}'")
            memory_usage = out
        except Exception:
            pass

        log, created = ServerLog.objects.update_or_create(
            date=today,
            defaults={
                'ssh_blocked': ssh_blocked,
                'nginx_errors': nginx_errors,
                'nginx_requests': nginx_requests,
                'disk_usage': disk_usage,
                'memory_usage': memory_usage,
            }
        )

        action = '作成' if created else '更新'
        self.stdout.write(self.style.SUCCESS(
            f'サーバーログを{action}しました（{today}）: '
            f'SSH試行ブロック={ssh_blocked}, アクセス={nginx_requests}, '
            f'Nginxエラー={nginx_errors}, Disk={disk_usage}, Mem={memory_usage}'
        ))
