"""スプレッドシート担当エージェント — Googleスプレッドシートの作成・読み書き"""

from actions.sheets import SheetsActions
from agents.base import BaseAgent

TOOLS = [
    {"name": "sheets_create", "description": "Googleスプレッドシートを新規作成", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "sheets_read", "description": "スプレッドシートのデータを読み込む", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}}, "required": ["spreadsheet_id"]}},
    {"name": "sheets_write", "description": "スプレッドシートにデータを書き込む", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}, "values": {"type": "array"}}, "required": ["spreadsheet_id", "range", "values"]}},
    {"name": "sheets_append", "description": "スプレッドシートにデータを追記する", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}, "values": {"type": "array"}}, "required": ["spreadsheet_id", "range", "values"]}},
    {"name": "sheets_list_sheets", "description": "スプレッドシートのシート一覧を取得", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}}, "required": ["spreadsheet_id"]}},
    {"name": "sheets_add_sheet", "description": "スプレッドシートにシートを追加", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "sheet_name": {"type": "string"}}, "required": ["spreadsheet_id", "sheet_name"]}},
]

SYSTEM_PROMPT = """あなたはGoogleスプレッドシートの専門家です。
スプレッドシートの作成・データ読み書き・編集を担当します。

## 得意分野
- スプレッドシートの新規作成
- データの読み取り・書き込み・追記
- シートの追加・管理

## ルール
- 日本語で簡潔に結果を報告する
- スプレッドシートIDやURLを含めて報告する
- データのフォーマットを整えて表示する"""


class SheetsMgrAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="SheetsMgrAgent",
            role="Googleスプレッドシートの作成・読み書き・管理の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self.sheets = SheetsActions(creds)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "sheets_create": return self.sheets.create_spreadsheet(tool_input["title"])
                case "sheets_read": return self.sheets.read_sheet(tool_input["spreadsheet_id"], tool_input.get("range", "Sheet1"))
                case "sheets_write": return self.sheets.write_sheet(tool_input["spreadsheet_id"], tool_input["range"], tool_input["values"])
                case "sheets_append": return self.sheets.append_sheet(tool_input["spreadsheet_id"], tool_input["range"], tool_input["values"])
                case "sheets_list_sheets": return self.sheets.list_sheets(tool_input["spreadsheet_id"])
                case "sheets_add_sheet": return self.sheets.add_sheet(tool_input["spreadsheet_id"], tool_input["sheet_name"])
                case _: return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
