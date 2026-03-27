"""リサーチ担当エージェント — 情報収集・分析・質問回答"""

import anthropic
from config import ANTHROPIC_API_KEY


class ResearcherAgent:
    """Claudeの知識を活用して調査・分析・質問回答を行う"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.name = "ResearcherAgent"
        self.role = "リサーチ・情報分析・質問回答の専門家"

    def run(self, task: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""あなたは優秀なリサーチャーです。
ユーザーの質問に対して、正確で分かりやすい回答を提供します。

## 得意分野
- 技術的な質問への回答
- ビジネス・市場調査
- 概念の説明・比較分析
- アイデアのブレインストーミング
- 文章の要約・翻訳

## ルール
- 日本語で簡潔に回答する
- 不確かな情報は「確認が必要」と明記する
- 複雑な内容は箇条書きや構造化して説明する
- 必要に応じて具体例を挙げる""",
            messages=[{"role": "user", "content": task}],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "回答を生成できませんでした。"
