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
from linebot.v3.webhooks import ImageMessageContent, TextMessageContent
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

# Agent は起動時に1回だけ初期化
from agent import LineAgent, get_google_creds
from actions.calendar import CalendarActions
from scheduler import create_scheduler

agent = LineAgent()

# スケジューラー用のカレンダーアクション
_creds = get_google_creds()
_calendar_for_scheduler = CalendarActions(_creds)


@asynccontextmanager
async def lifespan(app):
    """アプリ起動時にスケジューラーを開始、終了時に停止"""
    scheduler = create_scheduler(send_line_message, _calendar_for_scheduler, AUTHORIZED_USER_ID)
    scheduler.start()
    print(f"⏰ スケジューラー起動 — 朝の通知が有効です")
    yield
    scheduler.shutdown()
    print("⏰ スケジューラー停止")


app = FastAPI(lifespan=lifespan)
parser = WebhookParser(LINE_CHANNEL_SECRET)


async def send_line_message(user_id: str, text: str) -> None:
    """LINEにプッシュメッセージを送信（4999文字ごとに分割）"""
    chunks = [text[i : i + 4999] for i in range(0, len(text), 4999)]
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    async with AsyncApiClient(configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)
        for chunk in chunks[:5]:  # 最大5メッセージ
            await line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=chunk)],
                )
            )


async def download_line_image(message_id: str) -> bytes:
    """LINE APIから画像をダウンロード"""
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        resp.raise_for_status()
        return resp.content


async def process_message(user_id: str, text: str) -> None:
    """バックグラウンドでテキストメッセージを処理してLINEに返信"""
    try:
        await send_line_message(user_id, "⚙️ 処理中...")

        # Claude Agent を実行（同期処理をスレッドプールで実行）
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, agent.run, text)

        await send_line_message(user_id, response)

    except Exception as e:
        await send_line_message(user_id, f"❌ エラーが発生しました:\n{str(e)}")


async def process_image(user_id: str, message_id: str) -> None:
    """バックグラウンドで画像メッセージを処理してLINEに返信"""
    try:
        await send_line_message(user_id, "🖼️ 画像を分析中...")

        # 画像をダウンロード
        image_data = await download_line_image(message_id)
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Claude Vision で画像を分析
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, agent.run_with_image, image_b64
        )

        await send_line_message(user_id, response)

    except Exception as e:
        await send_line_message(user_id, f"❌ 画像処理エラー:\n{str(e)}")


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

        # テキストメッセージ
        if isinstance(event.message, TextMessageContent):
            background_tasks.add_task(
                process_message,
                user_id=user_id,
                text=event.message.text,
            )
        # 画像メッセージ
        elif isinstance(event.message, ImageMessageContent):
            background_tasks.add_task(
                process_image,
                user_id=user_id,
                message_id=event.message.id,
            )

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "message": "LINE Agent is running 🤖"}
