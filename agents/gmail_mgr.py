"""Gmail担当エージェント — メール送受信・検索・管理"""

from actions.gmail import GmailActions
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "gmail_send",
        "description": "メールを送信する",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "宛先メールアドレス"},
                "subject": {"type": "string", "description": "件名"},
                "body": {"type": "string", "description": "本文"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "gmail_search",
        "description": "メールを検索する（Gmailの検索クエリ対応: from:, subject:, is:unread 等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索クエリ（例: 'from:example@gmail.com', 'subject:請求書', 'is:unread'）"},
                "max_results": {"type": "integer", "description": "最大件数（デフォルト10）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "gmail_read",
        "description": "メールIDを指定して本文を読む",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "メールID"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_unread",
        "description": "未読メール一覧を取得する",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "最大件数（デフォルト10）"},
            },
        },
    },
]

SYSTEM_PROMPT = """あなたはGmailメール管理の専門家です。
メールの送信・検索・閲覧を担当します。

## 得意分野
- メール送信（日本語・英語対応）
- メール検索（送信者、件名、未読などの条件検索）
- メール閲覧・内容要約
- 未読メールの確認

## ルール
- メール送信前に宛先・件名・本文を必ず確認する
- 日本語で簡潔に結果を報告する
- メール本文が長い場合は要約して報告する
- 個人情報の取り扱いに注意する"""


class GmailMgrAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="GmailMgrAgent",
            role="Gmailメール送受信・検索・管理の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self.gmail = GmailActions(creds)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "gmail_send":
                    return self.gmail.send_email(tool_input["to"], tool_input["subject"], tool_input["body"])
                case "gmail_search":
                    return self.gmail.search_emails(tool_input["query"], tool_input.get("max_results", 10))
                case "gmail_read":
                    return self.gmail.read_email(tool_input["message_id"])
                case "gmail_unread":
                    return self.gmail.list_unread(tool_input.get("max_results", 10))
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
