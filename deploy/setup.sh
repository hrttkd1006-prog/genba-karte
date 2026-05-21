#!/bin/bash
# ============================================================
# げんばカルテ VPS セットアップスクリプト
# Ubuntu 22.04 LTS 対応
# 使い方: sudo bash setup.sh
# ============================================================

set -e  # エラーで即停止

# ── 設定（ここだけ変更する） ────────────────────────────
DOMAIN="genba-karte.jp"           # 取得したドメイン
APP_USER="genba"                   # アプリ実行ユーザー
APP_DIR="/home/$APP_USER/app"      # アプリのディレクトリ
REPO_URL="https://github.com/hrttkd1006-prog/genba-karte.git"
# ────────────────────────────────────────────────────────────

echo "========================================"
echo " げんばカルテ セットアップ開始"
echo "========================================"

# ── 1. システム更新 ──────────────────────────────────────
echo "[1/10] システムを更新中..."
apt-get update -y && apt-get upgrade -y

# ── 2. 必要パッケージインストール ────────────────────────
echo "[2/10] 必要パッケージをインストール中..."
apt-get install -y \
    python3 python3-pip python3-venv \
    nginx \
    mysql-server libmysqlclient-dev \
    certbot python3-certbot-nginx \
    git curl ufw \
    pkg-config gcc

# ── 3. アプリユーザー作成 ────────────────────────────────
echo "[3/10] アプリユーザーを作成中..."
if ! id "$APP_USER" &>/dev/null; then
    adduser --disabled-password --gecos "" $APP_USER
fi

# ── 4. コードをクローン ──────────────────────────────────
echo "[4/10] コードをクローン中..."
sudo -u $APP_USER git clone $REPO_URL $APP_DIR 2>/dev/null || \
    (cd $APP_DIR && sudo -u $APP_USER git pull)

# ── 5. Python仮想環境・依存関係 ──────────────────────────
echo "[5/10] Python環境をセットアップ中..."
sudo -u $APP_USER python3 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

# ── 6. MySQL セットアップ ────────────────────────────────
echo "[6/10] MySQLをセットアップ中..."
systemctl start mysql
systemctl enable mysql

# DB・ユーザー作成（パスワードは後で.envに設定）
mysql -e "CREATE DATABASE IF NOT EXISTS genba_karte CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS 'genba_user'@'localhost' IDENTIFIED BY 'CHANGE_THIS_PASSWORD';"
mysql -e "GRANT ALL PRIVILEGES ON genba_karte.* TO 'genba_user'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

echo ""
echo "⚠️  MySQLパスワードを変更してください："
echo "   mysql -e \"ALTER USER 'genba_user'@'localhost' IDENTIFIED BY '新しいパスワード';\""
echo ""

# ── 7. .env ファイル作成 ─────────────────────────────────
echo "[7/10] .envファイルを作成中..."
if [ ! -f "$APP_DIR/.env" ]; then
    cat > $APP_DIR/.env << 'EOF'
# ── 必ず変更する項目 ──────────────────────────────
SECRET_KEY=ここに新しいSECRET_KEYを入力
DEBUG=False
ALLOWED_HOSTS=genba-karte.jp,www.genba-karte.jp

# Database
DB_ENGINE=mysql
DB_NAME=genba_karte
DB_USER=genba_user
DB_PASSWORD=CHANGE_THIS_PASSWORD
DB_HOST=localhost
DB_PORT=3306

# Anthropic
ANTHROPIC_API_KEY=ここにAPIキーを入力

# SendGrid
SENDGRID_API_KEY=ここにAPIキーを入力
DEFAULT_FROM_EMAIL=noreply@genba-karte.jp

# Site
SITE_URL=https://genba-karte.jp

# 管理パネルURL
PANEL_URL_PREFIX=ここにランダム文字列を入力

# 管理者通知メール
ADMIN_NOTIFY_EMAIL=hrttkd1006@gmail.com
EOF
    chown $APP_USER:$APP_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    echo "⚠️  $APP_DIR/.env を編集してください！"
fi

# ── 8. Django セットアップ ───────────────────────────────
echo "[8/10] Djangoをセットアップ中..."
cd $APP_DIR
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py migrate
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py collectstatic --noinput

# ── 9. Gunicorn サービス設定 ─────────────────────────────
echo "[9/10] Gunicornサービスを設定中..."
cat > /etc/systemd/system/genba-karte.service << EOF
[Unit]
Description=Gunicorn daemon for genba-karte
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn \\
    --workers 3 \\
    --bind unix:$APP_DIR/gunicorn.sock \\
    config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable genba-karte
systemctl start genba-karte

# ── 10. Nginx 設定 ───────────────────────────────────────
echo "[10/10] Nginxを設定中..."
cat > /etc/nginx/sites-available/genba-karte << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root $APP_DIR/staticfiles;
    }

    location /media/ {
        root $APP_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/gunicorn.sock;
    }
}
EOF

ln -sf /etc/nginx/sites-available/genba-karte /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# ── ファイアウォール設定 ─────────────────────────────────
echo "ファイアウォールを設定中..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# ── SSL証明書取得 ────────────────────────────────────────
echo "SSL証明書を取得中..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m hrttkd1006@gmail.com

echo ""
echo "========================================"
echo " セットアップ完了！"
echo "========================================"
echo ""
echo "⚠️  次にやること："
echo "  1. $APP_DIR/.env を編集して本番用の値を設定する"
echo "  2. MySQLのパスワードを変更する"
echo "  3. python manage.py createsuperuser でスタッフユーザーを作成する"
echo "  4. systemctl restart genba-karte で再起動する"
echo ""
echo " サイトURL: https://$DOMAIN"
echo "========================================"
