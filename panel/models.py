from django.db import models


class ServerLog(models.Model):
    date = models.DateField('日付', unique=True)
    ssh_blocked = models.IntegerField('SSH不正試行ブロック数', default=0)
    nginx_errors = models.IntegerField('Nginxエラー数', default=0)
    nginx_requests = models.IntegerField('総アクセス数', default=0)
    disk_usage = models.CharField('ディスク使用率', max_length=20, blank=True)
    memory_usage = models.CharField('メモリ使用率', max_length=20, blank=True)
    notes = models.TextField('備考', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'サーバーログ'
        verbose_name_plural = 'サーバーログ'
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} のサーバーログ"
