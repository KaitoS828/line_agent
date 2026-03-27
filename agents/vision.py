"""画像分析担当エージェント — Claude Visionによる画像認識"""

import anthropic
from config import ANTHROPIC_API_KEY

IMAGE_ANALYSIS_PROMPT = """あなたはLINEで送られてきた画像を分析するAIアシスタントです。
画像の内容を日本語で分かりやすく説明してください。

以下のような分析を行ってください：
- 画像に何が写っているかの説明
- テキストが含まれている場合はOCR（文字起こし）
- レシートや請求書の場合は金額や店名などの要点を抽出
- 名刺の場合は連絡先情報を整理
- スクリーンショットの場合は内容の要約
- 料理の写真の場合は料理名の推測やカロリーの概算
- その他、画像から読み取れる有用な情報

簡潔かつ実用的に回答してください。"""


class VisionAgent:
    """Claude Visionで画像を分析"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.name = "VisionAgent"
        self.role = "画像分析・OCR・写真認識の専門家"

    def run(self, task: str) -> str:
        """テキストベースの指示（通常は使わない）"""
        return "画像を送ってください。分析を行います。"

    def analyze(self, image_b64: str) -> str:
        """base64エンコードされた画像を分析"""
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=IMAGE_ANALYSIS_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "この画像を分析してください。",
                        },
                    ],
                }
            ],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "画像を確認しましたが、特にコメントはありません。"
