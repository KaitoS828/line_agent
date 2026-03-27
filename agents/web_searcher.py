"""Web検索担当エージェント — リアルタイムのウェブ検索・情報収集"""

from actions import web_search
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "web_search",
        "description": "ウェブ検索を実行してリアルタイムの情報を取得する",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索クエリ"},
                "max_results": {"type": "integer", "description": "最大結果数（デフォルト3）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_page_content",
        "description": "指定URLのページ内容を取得する",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "取得するURL"},
            },
            "required": ["url"],
        },
    },
]

SYSTEM_PROMPT = """あなたはWeb検索の専門家です。
リアルタイムのウェブ検索を使って、最新の情報を収集・分析します。

## 得意分野
- 最新ニュース・トレンドの検索
- 技術情報・ドキュメントの検索
- 価格・レビュー・比較情報の検索
- 特定のページ内容の取得・要約

## ルール
- 日本語で簡潔に結果を報告する
- 情報源（URL）を必ず含める
- 複数のソースを比較して正確性を担保する
- 検索結果が不十分な場合はクエリを変えて再検索する
- 検索は2段階で行う
  1) 初回（深掘り指定がない）: web_searchは1回だけ実行し、短く要点を返す。最後に「必要なら深掘りして再検索する」と案内する
  2) 深掘り依頼あり（例: もっと詳しく、深掘り、比較して）: 複数回のweb_searchと必要なget_page_contentを使って、根拠付きで詳しく返す"""


class WebSearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="WebSearcherAgent",
            role="リアルタイムWeb検索・最新情報収集の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "web_search":
                    return web_search.search(
                        tool_input["query"],
                        tool_input.get("max_results", 3),
                    )
                case "get_page_content":
                    return web_search.get_page_content(tool_input["url"])
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
