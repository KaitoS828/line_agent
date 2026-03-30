"""環境変数の一元管理 — すべての設定値をここで定義"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── LINE ──────────────────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_AUTHORIZED_USER_ID = os.environ["LINE_AUTHORIZED_USER_ID"]

# ── AI API ────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# 後方互換: 既存実装が参照している場合に備えて残す
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", GEMINI_API_KEY)

# ── Google ────────────────────────────────────────────────────
GOOGLE_TOKEN_JSON = os.environ.get("GOOGLE_TOKEN_JSON", "")

# ── Supabase ──────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ── Web検索 ───────────────────────────────────────────────────
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")

# ── Threads ───────────────────────────────────────────────────
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")

# ── 天気 ──────────────────────────────────────────────────────
WEATHER_CITY = os.environ.get("WEATHER_CITY", "Tokyo")

# ── スケジューラー（任意 — デフォルト値あり）─────────────────
MORNING_NOTIFY_HOUR = int(os.environ.get("MORNING_NOTIFY_HOUR", "7"))
MORNING_NOTIFY_MINUTE = int(os.environ.get("MORNING_NOTIFY_MINUTE", "0"))
EVENING_NOTIFY_HOUR = int(os.environ.get("EVENING_NOTIFY_HOUR", "21"))
EVENING_NOTIFY_MINUTE = int(os.environ.get("EVENING_NOTIFY_MINUTE", "0"))
