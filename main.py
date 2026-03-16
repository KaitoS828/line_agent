import asyncio
import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from linebot.v3.webhook import (
    InvalidSignatureError,
    MessageEvent,
    WebhookParser,
)
from linebot.v3.webhooks import TextMessageContent
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

app = FastAPI()
parser = WebhookParser(LINE_CHANNEL_SECRET)

# Agent は起動時に1回だけ初期化
from agent import LineAgent

agent = LineAgent()


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


async def process_message(user_id: str, text: str) -> None:
    """バックグラウンドでメッセージを処理してLINEに返信"""
    try:
        await send_line_message(user_id, "⚙️ 処理中...")

        # Claude Agent を実行（同期処理をスレッドプールで実行）
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, agent.run, text)

        await send_line_message(user_id, response)

    except Exception as e:
        await send_line_message(user_id, f"❌ エラーが発生しました:\n{str(e)}")


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if isinstance(event, MessageEvent) and isinstance(
            event.message, TextMessageContent
        ):
            user_id = event.source.user_id
            if user_id != AUTHORIZED_USER_ID:
                # 認証されていないユーザーは無視
                continue
            background_tasks.add_task(
                process_message,
                user_id=user_id,
                text=event.message.text,
            )

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "message": "LINE Agent is running 🤖"}
