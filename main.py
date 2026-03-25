"""LINE Agent — FastAPI エントリポイント

LINEからのWebhookを受け取り、CEO Agentに処理を委譲する。
CEOが専門エージェント軍団を統括し、結果をLINEに返信する。
"""

import asyncio
import base64
import os

import httpx
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from linebot.v3.webhook import (
    InvalidSignatureError,
    MessageEvent,
    WebhookParser,
)
from linebot.v3.webhooks import AudioMessageContent, ImageMessageContent, TextMessageContent
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    PushMessageRequest,
    TextMessage,
)

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
AUTHORIZED_USER_ID = os.environ["LINE_AUTHORIZED_USER_ID"]

# ── CEO 初期化 ─────────────────────────────────────────────────
from ceo import CEOAgent, get_google_creds
from actions.calendar import CalendarActions
from scheduler import create_scheduler

ceo = CEOAgent()

# スケジューラー用のカレンダーアクション
_creds = get_google_creds()
_calendar_for_scheduler = CalendarActions(_creds)


# ── アプリ起動/停止 ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app):
    """起動時にスケジューラーを開始、停止時にシャットダウン"""
    scheduler = create_scheduler(send_line_message, _calendar_for_scheduler, AUTHORIZED_USER_ID)
    scheduler.start()
    print("⏰ スケジューラー起動 — 朝の通知が有効です")
    yield
    scheduler.shutdown()
    print("⏰ スケジューラー停止")


app = FastAPI(lifespan=lifespan)
parser = WebhookParser(LINE_CHANNEL_SECRET)


# ── LINE送信 ───────────────────────────────────────────────────

async def send_line_message(user_id: str, text: str) -> None:
    """LINEにプッシュメッセージを送信（4999文字ごとに分割）"""
    chunks = [text[i : i + 4999] for i in range(0, len(text), 4999)]
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    async with AsyncApiClient(configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)
        for chunk in chunks[:5]:
            await line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=chunk)],
                )
            )


async def download_line_content(message_id: str) -> bytes:
    """LINE APIからコンテンツ（画像・音声等）をダウンロード"""
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        resp.raise_for_status()
        return resp.content


# ── メッセージ処理（バックグラウンドタスク）─────────────────────

async def process_text(user_id: str, text: str) -> None:
    """テキスト → CEOが判断して適切なエージェントに委譲"""
    try:
        await send_line_message(user_id, "⚙️ 処理中...")
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, ceo.process_text, text)
        await send_line_message(user_id, response)
    except Exception as e:
        await send_line_message(user_id, f"❌ エラーが発生しました:\n{str(e)}")


async def process_image(user_id: str, message_id: str) -> None:
    """画像 → CEOがVisionAgentに委譲"""
    try:
        await send_line_message(user_id, "🖼️ 画像を分析中...")
        image_data = await download_line_content(message_id)
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, ceo.process_image, image_b64)
        await send_line_message(user_id, response)
    except Exception as e:
        await send_line_message(user_id, f"❌ 画像処理エラー:\n{str(e)}")


async def process_audio(user_id: str, message_id: str) -> None:
    """音声 → CEOがTranscriberAgentに委譲"""
    try:
        await send_line_message(user_id, "🎙️ 音声を文字起こし中...")
        audio_data = await download_line_content(message_id)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, ceo.process_audio, audio_data)
        await send_line_message(user_id, response)
    except Exception as e:
        await send_line_message(user_id, f"❌ 音声処理エラー:\n{str(e)}")


# ── Webhook ────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        user_id = event.source.user_id
        if user_id != AUTHORIZED_USER_ID:
            continue

        if isinstance(event.message, TextMessageContent):
            background_tasks.add_task(process_text, user_id, event.message.text)
        elif isinstance(event.message, ImageMessageContent):
            background_tasks.add_task(process_image, user_id, event.message.id)
        elif isinstance(event.message, AudioMessageContent):
            background_tasks.add_task(process_audio, user_id, event.message.id)

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "message": "LINE Agent is running 🤖"}
