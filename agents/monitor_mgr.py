"""監視管理担当エージェント — Webサイト変更検知・キーワードアラート"""

from agents.base import BaseAgent

TOOLS = [
    {
        "name": "monitor_add",
        "description": "新しい監視対象を追加する",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "監視対象の名前（例: Hacker News）"},
                "type": {
                    "type": "string",
                    "enum": ["website_change", "keyword_alert"],
                    "description": "監視タイプ: website_change（ページ変更検知）またはkeyword_alert（キーワード新着検索）",
                },
                "url": {"type": "string", "description": "監視するURL（website_changeの場合）"},
                "keyword": {"type": "string", "description": "監視するキーワード（keyword_alertの場合）"},
            },
            "required": ["name", "type"],
        },
    },
    {
        "name": "monitor_list",
        "description": "監視対象の一覧を表示する",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "monitor_remove",
        "description": "監視を停止・削除する",
        "input_schema": {
            "type": "object",
            "properties": {
                "monitor_id": {"type": "string", "description": "停止する監視のID"},
            },
            "required": ["monitor_id"],
        },
    },
    {
        "name": "monitor_check",
        "description": "全監視対象を今すぐチェックする",
        "input_schema": {"type": "object", "properties": {}},
    },
]

SYSTEM_PROMPT = """あなたはWeb監視の専門家です。
ユーザーが指定したWebサイトやキーワードを定期的に監視し、変更があれば通知します。

## 監視タイプ
1. **website_change**: 指定URLのページ内容が変わったら通知
2. **keyword_alert**: 指定キーワードの検索結果に新しい情報が出たら通知

## ルール
- 日本語で簡潔に報告する
- URLの監視にはwebsite_changeを使う
- ニュースやトピックの監視にはkeyword_alertを使う
- ユーザーが「監視して」「ウォッチして」「通知して」と言ったら監視追加と判断する"""


class MonitorMgrAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MonitorMgrAgent",
            role="Webサイト変更検知・キーワード監視アラートの専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        from actions.monitors import add_monitor, list_monitors, remove_monitor, check_all_monitors

        try:
            match tool_name:
                case "monitor_add":
                    config = {}
                    if tool_input.get("url"):
                        config["url"] = tool_input["url"]
                    if tool_input.get("keyword"):
                        config["keyword"] = tool_input["keyword"]
                    return add_monitor(
                        tool_input["name"],
                        tool_input["type"],
                        config,
                    )
                case "monitor_list":
                    return list_monitors()
                case "monitor_remove":
                    return remove_monitor(tool_input["monitor_id"])
                case "monitor_check":
                    alerts = check_all_monitors()
                    if alerts:
                        return "\n\n".join(alerts)
                    return "✅ 全監視対象に変更はありませんでした"
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
