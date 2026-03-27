"""レポート作成担当エージェント — Web調査 → レポート → Google Docs/PDF"""

from actions.report import create_report_pipeline, research_topic, generate_report
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "create_report",
        "description": "トピックについてWeb調査し、レポートをGoogle DocsとPDFで作成する。結果のリンクを返す。",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "調査・レポートのトピック"},
                "folder_id": {"type": "string", "description": "保存先のGoogle DriveフォルダID（省略可）"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "research_only",
        "description": "トピックについてWeb検索で情報収集のみ行う（レポート化しない）",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "調査するトピック"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_report_text",
        "description": "収集済みの情報からレポート文章のみ生成する（Docs/PDF保存しない）",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "レポートのタイトル/トピック"},
                "research_data": {"type": "string", "description": "レポートの元になる情報"},
            },
            "required": ["topic", "research_data"],
        },
    },
]

SYSTEM_PROMPT = """あなたはリサーチ＆レポート作成の専門家です。
ユーザーの依頼に応じて、Web調査を行い、構造化されたレポートを作成します。

## 得意分野
- トピックのWeb調査・情報収集
- 調査結果のレポート化（Google Docs + PDF）
- 情報の構造化・要約

## ツールの使い分け
- 「レポートにして」「PDFにして」「まとめて」→ create_report（調査+Docs+PDF一括）
- 「調べて」「検索して」→ research_only（調査のみ）
- テキストだけでレポートが欲しい時 → generate_report_text

## ルール
- 日本語で簡潔に報告する
- create_reportの結果にはGoogle DocsとPDFのリンクが含まれる
- レポートは事実ベースで、不確かな情報は明記する"""


class ReportWriterAgent(BaseAgent):
    def __init__(self, drive_service=None):
        super().__init__(
            name="ReportWriterAgent",
            role="Web調査 → レポート作成 → Google Docs/PDF出力の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self.drive_service = drive_service

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "create_report":
                    if not self.drive_service:
                        return "❌ Google Drive未接続のためPDF作成できません"
                    return create_report_pipeline(
                        self.drive_service,
                        tool_input["topic"],
                        tool_input.get("folder_id"),
                    )
                case "research_only":
                    return research_topic(tool_input["topic"])
                case "generate_report_text":
                    return generate_report(
                        tool_input["topic"],
                        tool_input["research_data"],
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
