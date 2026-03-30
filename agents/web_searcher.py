"""Web検索担当エージェント — ウェブ検索・YouTube・Twitter情報収集"""

from actions import web_search, youtube, twitter
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
        "description": "指定URLのページ内容を取得する（Jina Reader使用）",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "取得するURL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "youtube_transcript",
        "description": "YouTube動画の字幕・トランスクリプトを取得して要約する",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube動画のURL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "twitter_search",
        "description": "Twitter/Xでツイートを検索する",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索クエリ"},
                "max_results": {"type": "integer", "description": "最大件数（デフォルト10）"},
            },
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """あなたはWeb検索の専門家です。
ウェブ検索・YouTube字幕取得・Twitter検索を使って最新情報を収集・分析します。

## 得意分野
- 最新ニュース・トレンドの検索
- 技術情報・ドキュメントの検索
- YouTube動画の内容把握（字幕から要約）
- Twitter/Xのトレンドや反応の収集
- 特定のページ内容の取得・要約

## ルール
- 日本語で簡潔に結果を報告する
- 情報源（URL）を必ず含める
- YouTubeのURLが来たらyoutube_transcriptを使う
- Twitter/Xの検索依頼はtwitter_searchを使う
- 検索は2段階で行う
  1) 初回: 1回だけ検索して要点を短く返す
  2) 深掘り依頼時: 複数検索・ページ取得を組み合わせて詳しく返す"""


class WebSearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="WebSearcherAgent",
            role="リアルタイムWeb検索・YouTube字幕取得・Twitter検索の専門家",
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
                case "youtube_transcript":
                    info = youtube.get_video_info(tool_input["url"])
                    transcript = youtube.get_transcript(tool_input["url"])
                    return f"[動画情報]\n{info}\n\n[字幕]\n{transcript}"
                case "twitter_search":
                    return twitter.search_tweets(
                        tool_input["query"],
                        tool_input.get("max_results", 10),
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
