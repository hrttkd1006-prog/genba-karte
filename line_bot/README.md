# line_bot

げんばカルテのLINE公式アカウント連携アプリ（**仮実装段階**）。

既存の accounts / hospitals / reviews / jobs などのモデル・ビューには
**一切影響を与えない**構成。`INSTALLED_APPS` から外せば完全に切り離せる。

## 構成

```
line_bot/
├── apps.py            # AppConfig
├── models.py          # LineUser, LineMessage, ConversationState, LineInquiry
├── admin.py           # 管理画面登録
├── urls.py            # /line/webhook/
├── views.py           # Webhook受信・署名検証
├── handlers.py        # follow/unfollow/message のディスパッチ
├── flows.py           # 多段会話フロー（転職誘導・問い合わせ）
├── faq.py             # キーワードFAQマッチ
├── notifications.py   # プッシュ通知テンプレ + 配信ロジック
├── services.py        # LINE SDK ラッパー（reply, push）
├── tests.py           # ユニットテスト（外部通信なし）
├── management/commands/
│   ├── linebot_chat.py       # LINE接続なしで対話テストするCLI
│   └── linebot_broadcast.py  # 一斉プッシュ送信（既定ドライラン）
└── migrations/
```

## 動作の概要

### Webhook（本番経路）
```
LINEユーザー → LINEプラットフォーム
           → /line/webhook/ (views.webhook)
           → handlers.handle_message / handle_follow / handle_unfollow
           → 進行中フロー → flows.advance_active_flow
           → FAQ → faq.match_faq
           → デフォルト案内
           → services.reply_texts で返信
```

### 会話フロー
- **転職誘導**: 「転職」「求人相談」「エージェント」で開始 → エリア→施設→働き方→おすすめ提示
- **問い合わせ**: 「問い合わせ」等で開始 → 本文受付 → `LineInquiry` 保存
- 進行中はいつでも「キャンセル」で中止

### 動作確認（LINE接続不要）

```powershell
.\venv\Scripts\Activate.ps1
python manage.py makemigrations line_bot
python manage.py migrate
python manage.py linebot_chat --follow
```

`linebot_chat` は CLI でボットと対話できる。LINE Developers の設定前でも
ハンドラ・フロー・FAQ のロジック確認が可能。

### テスト

```powershell
python manage.py test line_bot
```

## セットアップ（LINE接続）

### 1. LINE Developers でチャネル作成

1. https://developers.line.biz/console/ にログイン
2. プロバイダー作成（例: `genba-karte`）
3. **Messaging API チャネル**を作成
4. 「チャネル基本設定」→ **Channel secret** を控える
5. 「Messaging API設定」→ **Channel access token（長期）** を発行
6. Messaging API設定で:
   - 応答メッセージ: **オフ**
   - あいさつメッセージ: 任意
   - Webhook の利用: **オン**
   - Webhook URL: `https://genba-karte.com/line/webhook/`

### 2. `.env` に追加

```
LINE_CHANNEL_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxx...
```

### 3. パッケージインストール

```powershell
pip install -r requirements.txt
python manage.py migrate
```

### 4. ローカルでWebhook動作確認

```powershell
python manage.py runserver
# 別ターミナル:
ngrok http 8000
```

ngrok のURLを LINE Developers の Webhook URL に一時設定して「検証」。

### 5. 本番（VPS）反映

```bash
ssh -i "C:/Users/Owner/.ssh/genba_vps" genba@160.251.176.193
cd /home/genba/app && git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
sudo systemctl restart genba-karte
```

本番 `.env` に LINE キーを追加、Webhook URL を `https://genba-karte.com/line/webhook/` に。

## 運用コマンド

### お知らせを一斉配信

```powershell
# ドライラン（DBにログだけ残す）
python manage.py linebot_broadcast --title "メンテナンスのお知らせ" --body "本日23時から〜"

# 実送信（LINE設定完了後）
python manage.py linebot_broadcast --title "..." --body "..." --send
```

## 今後の連携（段階的に）

枠組み完成後、げんばカルテ本体と接続するときに行う作業:

- [ ] `accounts.User` に `line_user_id` フィールド追加（LINE Login連携）
- [ ] `reviews/signals.py` で新着レビュー時に `notifications.send_to_followers` を呼ぶ
- [ ] `jobs/signals.py` で新着求人時に通知（病院フォロワーに絞る）
- [ ] LINEログイン用 OAuth コールバック (`/line/callback/`) 実装
- [ ] リッチメニュー画像作成 + 登録コマンド
- [ ] 転職誘導フローのおすすめロジックを medical_affiliate のアフィリンクと連携
