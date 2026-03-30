"""Threads投稿エージェント — 文章生成 → Threads投稿"""

from agents.base import BaseAgent
from actions import threads

TOOLS = [
    {
        "name": "post_text",
        "description": "テキストをThreadsに投稿する（500文字以内）",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "投稿するテキスト（500文字以内）"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "post_image",
        "description": "画像付きでThreadsに投稿する",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "投稿テキスト"},
                "image_url": {"type": "string", "description": "画像の公開URL（JPEG/PNG、8MB以内）"},
            },
            "required": ["text", "image_url"],
        },
    },
]

SYSTEM_PROMPT = """あなたはThreads（SNS）への投稿を担当するエージェントです。
ユーザーの依頼をもとに投稿文を作成し、Threadsに投稿します。

## 投稿文の作成ルール
- 500文字以内に収める
- 自然な日本語で、読みやすく
- 必要に応じてハッシュタグを2〜3個付ける（#広尾町 #NISSEBREW #ゲストハウス など文脈に合わせて）
- 宣伝っぽくなりすぎず、人間味のある文章にする
- ユーザーから「そのまま投稿して」と言われた場合は文章を変えずに投稿する

## ルール
- 投稿前に投稿文をユーザーに確認させる（「この内容で投稿していい？」と聞く）
- ただし「確認なしで投稿して」「そのまま投稿して」と言われた場合は即投稿する
- 投稿後は結果のURLを報告する"""


class ThreadsPosterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ThreadsPosterAgent",
            role="Threads（SNS）への投稿文生成・投稿の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "post_text":
                    return threads.post_text(tool_input["text"])
                case "post_image":
                    return threads.post_image(tool_input["text"], tool_input["image_url"])
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
