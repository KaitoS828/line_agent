"""CEO Agent — 全エージェントを統括する司令塔

ユーザー（LINE）からのメッセージを受け取り、適切な専門エージェントに
タスクを委譲し、結果をレビューしてユーザーに返答する。
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config import ANTHROPIC_API_KEY, GOOGLE_TOKEN_JSON, SUPABASE_URL
from agents import create_all_agents, get_agent_directory
from actions.memory import save_message, get_conversation_context

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_google_creds() -> Credentials:
    creds = None
    token_json_str = GOOGLE_TOKEN_JSON
    if token_json_str:
        creds = Credentials.from_authorized_user_info(json.loads(token_json_str), SCOPES)
    elif TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if TOKEN_FILE.exists():
                TOKEN_FILE.write_text(creds.to_json())
        else:
            raise RuntimeError("Google認証が必要です。python auth_drive.py を実行してください。")
    return creds


# ── CEOの委譲ツール ─────────────────────────────────────────────

DELEGATE_TOOL = {
    "name": "delegate",
    "description": "専門エージェント（社員）にタスクを委譲する。複数のエージェントに順番に委譲することも可能。",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "description": "委譲先エージェント名",
            },
            "task": {
                "type": "string",
                "description": "エージェントに渡すタスクの詳細な指示",
            },
        },
        "required": ["agent", "task"],
    },
}


class CEOAgent:
    """LINE Agent の CEO — 全エージェントを統括"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.creds = get_google_creds()
        self.agents = create_all_agents(self.creds)
        self.agent_directory = get_agent_directory(self.agents)

        # 性格ファイル読み込み
        personality_file = Path(__file__).parent / "personality.md"
        self.personality = personality_file.read_text(encoding="utf-8") if personality_file.exists() else ""
        personality = self.personality

        # CEOのシステムプロンプト
        self.system_prompt = f"""LINE AIアシスタント。ユーザーの依頼を社員に委譲し、結果を報告する。

{personality}

【社員一覧】
{self.agent_directory}

【委譲ルール】
- 作業は必ず社員に委譲。挨拶・雑談のみ直接回答可
- 複数社員への連続委譲OK。image_creatorのIMAGE_URL形式はそのまま返す
- Web検索: 初回は1回だけ。「深掘りして」なら複数検索
- レポート系はreport_writer、画像生成はimage_creatorへ
- タスク指示は必要最小限に。「何をすべきか」だけ伝える。背景説明・文脈の再説明は不要

【出力ルール（最優先）】
- 必ずキャラ設定の口調で返答
- #見出し禁止。箇条書きは「・」か「→」
- 敬語（〜できます/いたします/ございます）禁止
- LINEチャットとして自然な長さ。長い一覧表は作らない"""

    # ── テキストメッセージ処理 ──────────────────────────────────

    def process_text(self, user_message: str, user_id: str = "default", on_delegate=None) -> str:
        """テキストメッセージを処理 — 適切なエージェントに委譲"""
        # 会話記憶: ユーザーメッセージを保存 & コンテキスト取得
        if SUPABASE_URL:
            try:
                save_message(user_id, "user", user_message)
                context = get_conversation_context(user_id)
            except Exception:
                context = ""
        else:
            context = ""

        # 現在の東京時刻を毎回動的に注入（API呼び出しなし・高速）
        JST = timezone(timedelta(hours=9))
        now_jst = datetime.now(JST)
        current_time_str = now_jst.strftime("%Y年%m月%d日（%A）%H:%M JST")
        # 曜日を日本語に変換
        weekday_ja = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        current_time_str = now_jst.strftime("%Y年%m月%d日") + f"（{weekday_ja[now_jst.weekday()]}）" + now_jst.strftime("%H:%M JST")

        system = self.system_prompt + f"\n\n## 現在の日時（必ずこれを基準に日付を解釈すること）\n{current_time_str}"
        if context:
            system += f"\n\n{context}"

        messages = [{"role": "user", "content": user_message}]

        for _ in range(15):
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                tools=[DELEGATE_TOOL],
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        result = block.text
                        # 会話記憶: 応答を保存
                        if SUPABASE_URL:
                            try:
                                save_message(user_id, "assistant", result)
                            except Exception:
                                pass
                        return result
                return "✅ 完了しました。"

            if response.stop_reason == "tool_use":
                if on_delegate:
                    on_delegate()
                    on_delegate = None  # 最初の委譲時のみ通知
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._delegate(block.input["agent"], block.input["task"])
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return "✅ 処理が完了しました。"

    # ── 画像メッセージ処理 ──────────────────────────────────────

    def process_image(self, image_b64: str) -> str:
        """画像メッセージ → VisionAgentに委譲 → CEOがレビューして返答"""
        # VisionAgent に直接委譲
        vision = self.agents["vision"]
        analysis = vision.analyze(image_b64)

        # CEOが結果をレビュー
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=f"あなたはAIアシスタントです。画像分析担当からの報告をユーザーにわかりやすく伝えてください。報告内容が十分であればそのまま伝え、補足が必要なら追加してください。簡潔に。\n\n## キャラクター設定（必ずこの口調で応答）\n{self.personality}\n\n## 口調・フォーマットの絶対ルール\n- マークダウンの見出し（#）は使わない\n- 箇条書きは「・」や「→」を使う。「-」「*」のマークダウン記法は使わない\n- 「〜できます」「〜いたします」「〜ございます」のような敬語は使わない",
            messages=[
                {
                    "role": "user",
                    "content": f"画像分析担当からの報告:\n\n{analysis}",
                }
            ],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return analysis

    # ── 音声メッセージ処理 ──────────────────────────────────────

    def process_audio(self, audio_data: bytes) -> str:
        """音声メッセージ → TranscriberAgentに委譲 → CEOがレビューして返答"""
        # TranscriberAgent に直接委譲
        transcriber = self.agents["transcriber"]
        result = transcriber.transcribe(audio_data)

        # CEOが結果をレビュー
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=f"あなたはAIアシスタントです。文字起こし担当からの報告をユーザーにわかりやすく伝えてください。議事録のフォーマットが適切であればそのまま伝えてください。簡潔に。\n\n## キャラクター設定（必ずこの口調で応答）\n{self.personality}\n\n## 口調・フォーマットの絶対ルール\n- マークダウンの見出し（#）は使わない\n- 箇条書きは「・」や「→」を使う。「-」「*」のマークダウン記法は使わない\n- 「〜できます」「〜いたします」「〜ございます」のような敬語は使わない",
            messages=[
                {
                    "role": "user",
                    "content": f"文字起こし担当からの報告:\n\n{result}",
                }
            ],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return result

    # ── 内部メソッド ───────────────────────────────────────────

    # 要約を省略するエージェント（画像URLなど構造データを返すもの）
    _NO_SUMMARIZE = {"image_creator", "report_writer"}
    # 要約を発動する文字数しきい値
    _SUMMARIZE_THRESHOLD = 2000

    def _delegate(self, agent_name: str, task: str) -> str:
        """社員にタスクを委譲して結果を受け取る。長い返答は要約して渡す"""
        agent = self.agents.get(agent_name)
        if not agent:
            available = ", ".join(self.agents.keys())
            return f"❌ 「{agent_name}」という社員は存在しません。利用可能: {available}"

        result = agent.run(task)

        # 短い・要約不要なエージェントはそのまま返す
        if len(result) <= self._SUMMARIZE_THRESHOLD or agent_name in self._NO_SUMMARIZE:
            return result

        # 長い返答をHaikuで要約してからCEOに渡す
        try:
            summary_response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=[{"role": "user", "content":
                    f"以下の報告を300文字以内で要点だけ箇条書きにしてください。重要な数値・URL・固有名詞は残すこと。\n\n{result[:6000]}"}],
            )
            for block in summary_response.content:
                if hasattr(block, "text"):
                    return block.text
        except Exception:
            pass

        # 要約失敗時は先頭2000文字で切る
        return result[:self._SUMMARIZE_THRESHOLD] + "…（以下省略）"
