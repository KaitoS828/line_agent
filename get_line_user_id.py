#!/usr/bin/env python3
"""
自分のLINE User IDを取得するためのツール
使い方:
1. python get_line_user_id.py でサーバー起動
2. 別ターミナルで: ngrok http 8080
3. LINE Developers でWebhook URLを ngrok_url/webhook_debug に設定
4. LINEで自分のBotにメッセージを送ると User ID が表示される
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from linebot.v3.webhook import WebhookParser, MessageEvent, InvalidSignatureError
from linebot.v3.webhooks import TextMessageContent

load_dotenv()

LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]

app = FastAPI()
parser = WebhookParser(LINE_CHANNEL_SECRET)


@app.post("/webhook_debug")
async def webhook_debug(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if isinstance(event, MessageEvent):
            user_id = event.source.user_id
            print(f"\n{'='*50}")
            print(f"✅ あなたのLINE User ID: {user_id}")
            print(f"{'='*50}")
            print(f".envに以下を設定してください:")
            print(f"LINE_AUTHORIZED_USER_ID={user_id}")

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    print("User ID取得サーバーを起動します (port 8080)")
    print("LINEでBotにメッセージを送ってください")
    uvicorn.run(app, host="0.0.0.0", port=8080)
