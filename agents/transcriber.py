"""文字起こし担当エージェント — 音声→テキスト→議事録"""

import tempfile

import anthropic
from openai import OpenAI
from config import ANTHROPIC_API_KEY, OPENAI_API_KEY

MEETING_MINUTES_PROMPT = """あなたは議事録作成の専門家です。
音声から文字起こしされたテキストを元に、構造化された議事録を作成してください。

## 出力フォーマット
📝 議事録

📅 日時: （推測できれば記載、できなければ省略）
👥 参加者: （推測できれば記載、できなければ省略）

■ 要約
（会議全体の要約を2-3文で）

■ 主な議題・内容
1. ...
2. ...

■ 決定事項
- ...

■ アクションアイテム（TODO）
- [ ] ...

■ その他メモ
- ...

## ルール
- 日本語で出力
- 文字起こしが会議でない場合（メモ、独り言、インタビューなど）は内容に合わせて柔軟にフォーマットを調整
- 重要なポイントを見逃さないようにする
- 不明瞭な部分は「（不明瞭）」と記載"""


class TranscriberAgent:
    """Whisperで文字起こし → Claudeで議事録作成"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.name = "TranscriberAgent"
        self.role = "音声の文字起こし・議事録作成の専門家"

    def run(self, task: str) -> str:
        """テキストベースの指示（通常は使わない）"""
        return "音声データを送ってください。文字起こしと議事録作成を行います。"

    def transcribe(self, audio_data: bytes) -> str:
        """音声データを文字起こしして議事録を作成"""
        # Whisper で文字起こし
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as tmp:
            tmp.write(audio_data)
            tmp.flush()
            with open(tmp.name, "rb") as audio_file:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja",
                )
        transcript_text = transcription.text

        if not transcript_text.strip():
            return "⚠️ 音声を認識できませんでした。もう一度お試しください。"

        # Claude で議事録作成
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=MEETING_MINUTES_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"以下の文字起こしテキストから議事録を作成してください:\n\n{transcript_text}",
                }
            ],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return f"🎙️ 文字起こし結果:\n{transcript_text}\n\n{'─' * 20}\n\n{block.text}"
        return f"🎙️ 文字起こし結果:\n{transcript_text}"
