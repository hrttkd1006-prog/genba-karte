from django.db import models


class LineUser(models.Model):
    """LINEユーザー。既存のgenba-karte Userとは独立。
    将来 user = OneToOneField('accounts.User', ...) を追加して紐づける。
    """
    line_user_id = models.CharField('LINE ユーザーID', max_length=64, unique=True)
    display_name = models.CharField('表示名', max_length=128, blank=True)
    picture_url = models.URLField('プロフィール画像', blank=True)
    is_followed = models.BooleanField('友だち登録中', default=True)
    followed_at = models.DateTimeField('登録日時', auto_now_add=True)
    unfollowed_at = models.DateTimeField('ブロック日時', null=True, blank=True)

    class Meta:
        verbose_name = 'LINEユーザー'
        verbose_name_plural = 'LINEユーザー'

    def __str__(self):
        return self.display_name or self.line_user_id


class LineMessage(models.Model):
    """受信メッセージのログ。動作確認用。"""
    DIRECTION_CHOICES = [
        ('in', '受信'),
        ('out', '送信'),
    ]
    line_user = models.ForeignKey(
        LineUser, on_delete=models.CASCADE, related_name='messages',
        null=True, blank=True,
    )
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    message_type = models.CharField('種別', max_length=32, blank=True)
    text = models.TextField('本文', blank=True)
    raw_event = models.JSONField('生イベント', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'LINEメッセージ'
        verbose_name_plural = 'LINEメッセージ'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_direction_display()}] {self.text[:30]}'


class ConversationState(models.Model):
    """多段会話の進行状態。

    flow_name: どのフローか（例: 'job_transfer', 'inquiry'）
    step: フロー内のステップ番号
    data: 各ステップで集めた回答（JSON）
    """
    line_user = models.OneToOneField(
        LineUser, on_delete=models.CASCADE, related_name='conversation_state',
    )
    flow_name = models.CharField(max_length=64)
    step = models.PositiveIntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '会話状態'
        verbose_name_plural = '会話状態'

    def __str__(self):
        return f'{self.line_user} / {self.flow_name} step={self.step}'


class LineInquiry(models.Model):
    """LINE経由で受け付けた問い合わせ。

    後で既存 Contact モデルに統合する選択肢もあるが、まずは独立で運用する。
    """
    STATUS_CHOICES = [
        ('new', '未対応'),
        ('replied', '返信済み'),
        ('closed', '完了'),
    ]
    line_user = models.ForeignKey(
        LineUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inquiries',
    )
    subject = models.CharField('件名', max_length=200, blank=True)
    body = models.TextField('本文')
    status = models.CharField('ステータス', max_length=16, choices=STATUS_CHOICES, default='new')
    admin_note = models.TextField('管理メモ', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'LINE問い合わせ'
        verbose_name_plural = 'LINE問い合わせ'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.line_user} / {self.body[:30]}'
