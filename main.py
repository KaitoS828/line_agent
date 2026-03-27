"""LINE Agent — FastAPI エントリポイント

LINEからのWebhookを受け取り、CEO Agentに処理を委譲する。
CEOが専門エージェント軍団を統括し、結果をLINEに返信する。
"""

import asyncio
import base64
import re

import httpx
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
    ImageMessage,
    PushMessageRequest,
    TextMessage,
)

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, LINE_AUTHORIZED_USER_ID
from actions.activity_log import log_request

AUTHORIZED_USER_ID = LINE_AUTHORIZED_USER_ID

# ── CEO 初期化 ─────────────────────────────────────────────────
from ceo import CEOAgent, get_google_creds
from actions.calendar import CalendarActions
from actions.gmail import GmailActions
from scheduler import create_scheduler

ceo = CEOAgent()

# スケジューラー用のサービス群
_creds = get_google_creds()
_services = {
    "calendar": CalendarActions(_creds),
    "gmail": GmailActions(_creds),
}


# ── アプリ起動/停止 ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app):
    """起動時にスケジューラーを開始、停止時にシャットダウン"""
    scheduler = create_scheduler(send_line_message, _services, AUTHORIZED_USER_ID)
    scheduler.start()
    print("⏰ スケジューラー起動 — 能動的通知が有効です")
    yield
    scheduler.shutdown()
    print("⏰ スケジューラー停止")


app = FastAPI(lifespan=lifespan)
parser = WebhookParser(LINE_CHANNEL_SECRET)


# ── LINE送信 ───────────────────────────────────────────────────

async def send_line_message(user_id: str, text: str) -> None:
    """LINEにプッシュメッセージを送信（4999文字ごとに分割）"""
    normalized_text = normalize_line_text(text)
    chunks = [normalized_text[i : i + 4999] for i in range(0, len(normalized_text), 4999)]
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


async def send_line_image(user_id: str, image_url: str) -> None:
    """LINEに画像メッセージを送信"""
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    async with AsyncApiClient(configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)
        await line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[
                    ImageMessage(
                        original_content_url=image_url,
                        preview_image_url=image_url,
                    )
                ],
            )
        )


def normalize_line_text(text: str) -> str:
    """LINE向けにテキスト整形（Markdownの*を抑止）"""
    # 箇条書きの先頭記号を統一
    text = re.sub(r"(?m)^\s*[\-\*]\s+", "・ ", text)
    # 太字・強調などで使われたアスタリスクを除去
    return text.replace("*", "")


def extract_line_image_payload(text: str) -> tuple[str, str]:
    """IMAGE_URL/CAPTION 形式の応答を抽出"""
    image_match = re.search(r"(?im)^IMAGE_URL:\s*(https?://\S+)\s*$", text)
    if not image_match:
        return "", ""
    caption_match = re.search(r"(?im)^CAPTION:\s*(.+)\s*$", text)
    caption = caption_match.group(1).strip() if caption_match else "画像できたよ！"
    return image_match.group(1).strip(), caption


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
        log_request("text")
        await send_line_message(user_id, "考え中にゃ！")
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, ceo.process_text, text, user_id)
        image_url, caption = extract_line_image_payload(response)
        if image_url:
            await send_line_image(user_id, image_url)
            await send_line_message(user_id, caption)
        else:
            await send_line_message(user_id, response)
    except Exception as e:
        await send_line_message(user_id, f"❌ エラーが発生しました:\n{str(e)}")


async def process_image(user_id: str, message_id: str) -> None:
    """画像 → CEOがVisionAgentに委譲"""
    try:
        log_request("image")
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
        log_request("audio")
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
