"""CEO Agent — 全エージェントを統括する司令塔

ユーザー（LINE）からのメッセージを受け取り、適切な専門エージェントに
タスクを委譲し、結果をレビューしてユーザーに返答する。
"""

import json
import os
from pathlib import Path

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from agents import create_all_agents, get_agent_directory

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_google_creds() -> Credentials:
    creds = None
    token_json_str = os.environ.get("GOOGLE_TOKEN_JSON")
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
        self.client = anthropic.Anthropic()
        self.creds = get_google_creds()
        self.agents = create_all_agents(self.creds)
        self.agent_directory = get_agent_directory(self.agents)

        # CEOのシステムプロンプト
        self.system_prompt = f"""あなたはLINE AIアシスタントの CEO（最高経営責任者）です。
ユーザーからのメッセージを受け取り、適切な専門エージェント（社員）にタスクを委譲し、
結果をレビューしてユーザーにわかりやすく報告します。

## あなたの社員一覧
{self.agent_directory}

## あなたの役割
1. ユーザーの意図を正確に理解する
2. 最適な社員（エージェント）を選んでタスクを委譲する
3. 1つのリクエストで複数の社員への委譲が可能（順番に実行）
4. 社員からの報告を確認し、必要に応じて追加指示を出す
5. 最終結果をユーザーに日本語で簡潔にまとめて報告する

## ルール
- 自分で直接作業はしない。必ず社員に委譲する
- 簡単な挨拶や雑談には、委譲せずに直接答えてもよい
- 社員からのエラー報告は、わかりやすくユーザーに伝える
- 複数の社員が必要な場合は、適切な順番で委譲する
- 報告は簡潔に。余計な前置きは不要"""

    # ── テキストメッセージ処理 ──────────────────────────────────

    def process_text(self, user_message: str) -> str:
        """テキストメッセージを処理 — 適切なエージェントに委譲"""
        messages = [{"role": "user", "content": user_message}]

        for _ in range(15):  # 複数エージェントへの連続委譲に対応
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=[DELEGATE_TOOL],
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return "✅ 完了しました。"

            if response.stop_reason == "tool_use":
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
            system="あなたはCEOです。画像分析担当からの報告をユーザーにわかりやすく伝えてください。報告内容が十分であればそのまま伝え、補足が必要なら追加してください。簡潔に。",
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
            system="あなたはCEOです。文字起こし担当からの報告をユーザーにわかりやすく伝えてください。議事録のフォーマットが適切であればそのまま伝えてください。簡潔に。",
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

    def _delegate(self, agent_name: str, task: str) -> str:
        """社員にタスクを委譲して結果を受け取る"""
        agent = self.agents.get(agent_name)
        if not agent:
            available = ", ".join(self.agents.keys())
            return f"❌ 「{agent_name}」という社員は存在しません。利用可能: {available}"
        return agent.run(task)
