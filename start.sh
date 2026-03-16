#!/bin/bash
set -e

cd "$(dirname "$0")"

# .env確認
if [ ! -f ".env" ]; then
    echo "❌ .env ファイルが見つかりません"
    echo "cp .env.example .env を実行して必要な値を設定してください"
    exit 1
fi

# ngrok起動（バックグラウンド）
echo "🚇 ngrok を起動中..."
ngrok http 8080 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 3

# ngrok URL取得
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(next(t['public_url'] for t in d['tunnels'] if t['proto']=='https'))" 2>/dev/null || echo "")

if [ -z "$NGROK_URL" ]; then
    echo "⚠️  ngrok URLの自動取得に失敗しました"
    echo "   手動で http://localhost:4040 を確認してください"
else
    echo ""
    echo "✅ ngrok URL: $NGROK_URL"
    echo "📌 LINE Webhook URL に設定してください:"
    echo "   $NGROK_URL/webhook"
    echo ""
fi

# サーバー起動
echo "🤖 LINE Agent サーバーを起動します (port 8080)..."
echo "終了するには Ctrl+C を押してください"
echo ""

cleanup() {
    echo ""
    echo "🛑 サーバーを停止しています..."
    kill $NGROK_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

uvicorn main:app --host 0.0.0.0 --port 8080 --reload

kill $NGROK_PID 2>/dev/null || true
