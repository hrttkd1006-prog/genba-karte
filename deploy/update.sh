#!/bin/bash
# ============================================================
# げんばカルテ アップデートスクリプト
# 使い方: bash update.sh
# ============================================================

set -e

APP_DIR="/home/genba/app"

echo "========================================"
echo " げんばカルテ アップデート開始"
echo "========================================"

cd $APP_DIR

echo "[1/4] 最新コードを取得中..."
git pull origin main

echo "[2/4] 依存関係を更新中..."
venv/bin/pip install -r requirements.txt

echo "[3/4] マイグレーション・静的ファイル収集..."
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput

echo "[4/4] Gunicornを再起動中..."
sudo systemctl restart genba-karte

echo ""
echo "✅ アップデート完了！"
echo "========================================"
