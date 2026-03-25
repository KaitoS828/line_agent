"""スケジュール管理担当エージェント — Googleカレンダー操作"""

from actions.calendar import CalendarActions
from agents.base import BaseAgent

TOOLS = [
    {"name": "calendar_list_events", "description": "Googleカレンダーの予定一覧を取得", "input_schema": {"type": "object", "properties": {"max_results": {"type": "integer"}, "calendar_id": {"type": "string"}}}},
    {"name": "calendar_create_event", "description": "Googleカレンダーに予定を作成", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "start": {"type": "string", "description": "ISO8601形式 例: 2026-03-17T10:00:00+09:00"}, "end": {"type": "string"}, "description": {"type": "string"}, "calendar_id": {"type": "string"}}, "required": ["title", "start", "end"]}},
    {"name": "calendar_update_event", "description": "Googleカレンダーの予定を更新", "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "title": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}, "description": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "calendar_delete_event", "description": "Googleカレンダーの予定を削除", "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "calendar_search_events", "description": "Googleカレンダーの予定を検索", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]

SYSTEM_PROMPT = """あなたはスケジュール管理の専門家です。
Googleカレンダーを使った予定の作成・確認・更新・削除を担当します。

## 得意分野
- 予定の作成・変更・キャンセル
- スケジュールの確認・検索
- 日程調整の提案

## ルール
- 日時はAsia/Tokyoタイムゾーン（+09:00）で扱う
- 日本語で簡潔に結果を報告する
- 予定作成時はISO8601形式（例: 2026-03-25T10:00:00+09:00）を使用する
- 終了時刻が指定されない場合は開始から1時間後をデフォルトにする"""


class CalendarMgrAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="CalendarMgrAgent",
            role="Googleカレンダーの予定管理（作成・確認・更新・削除）の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self.calendar = CalendarActions(creds)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "calendar_list_events": return self.calendar.list_events(tool_input.get("max_results", 10), tool_input.get("calendar_id", "primary"))
                case "calendar_create_event": return self.calendar.create_event(tool_input["title"], tool_input["start"], tool_input["end"], tool_input.get("description", ""), tool_input.get("calendar_id", "primary"))
                case "calendar_update_event": return self.calendar.update_event(tool_input["event_id"], tool_input.get("title"), tool_input.get("start"), tool_input.get("end"), tool_input.get("description"))
                case "calendar_delete_event": return self.calendar.delete_event(tool_input["event_id"], tool_input.get("calendar_id", "primary"))
                case "calendar_search_events": return self.calendar.search_events(tool_input["query"], tool_input.get("calendar_id", "primary"))
                case _: return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
