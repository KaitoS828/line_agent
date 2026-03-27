"""画像生成担当エージェント — プロンプトから画像を生成してURL返却"""

from actions.image_gen import generate_image_url
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "generate_image",
        "description": "入力プロンプトから画像を生成し、公開URLを返す",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "画像生成プロンプト"},
                "size": {
                    "type": "string",
                    "description": "画像サイズ（1024x1024 / 1024x1792 / 1792x1024）",
                },
            },
            "required": ["prompt"],
        },
    }
]

SYSTEM_PROMPT = """あなたは画像生成の専門家です。
ユーザーの要望に合わせて画像を1枚生成します。

## ルール
- まずgenerate_imageを使って画像URLを取得する
- 最終回答は次の形式のみで返す（厳守）
IMAGE_URL: <https://...>
CAPTION: <1行の短い説明>
- IMAGE_URL が取得できないときは、理由を短く日本語で返す"""


class ImageCreatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ImageCreatorAgent",
            role="画像生成の専門家。画像を作ってURLで返す",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "generate_image":
                    return generate_image_url(
                        prompt=tool_input["prompt"],
                        size=tool_input.get("size", "1024x1024"),
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
