"""タスク管理担当エージェント — TODOタスクの追加・完了・一覧・管理"""

from actions import tasks
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "task_add",
        "description": "新しいタスクを追加する",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "タスクのタイトル"},
                "due_date": {"type": "string", "description": "期限（YYYY-MM-DD形式、省略可）"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "優先度（デフォルト: medium）"},
                "category": {"type": "string", "description": "カテゴリ（例: 仕事, 個人, 買い物）"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "task_complete",
        "description": "タスクを完了にする",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "タスクID"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_delete",
        "description": "タスクを削除する",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "タスクID"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_list",
        "description": "タスク一覧を表示する",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "completed"], "description": "フィルタ（デフォルト: pending）"},
                "category": {"type": "string", "description": "カテゴリでフィルタ"},
            },
        },
    },
    {
        "name": "task_update",
        "description": "タスクの情報を更新する",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "タスクID"},
                "title": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "due_date": {"type": "string"},
                "category": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
]

SYSTEM_PROMPT = """あなたはタスク管理の専門家です。
ユーザーのTODOリストを管理します。

## 得意分野
- タスクの追加・完了・削除
- タスクの一覧表示・カテゴリ分け
- 優先度管理・期限管理
- タスクの整理・提案

## ルール
- 日本語で簡潔に報告する
- タスク追加時は優先度を適切に判断する
- 期限が近いタスクは注意を促す
- ユーザーが「タスク」「TODO」「やること」と言ったらタスク操作と判断する"""


class TaskMgrAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TaskMgrAgent",
            role="TODOタスク管理（追加・完了・一覧・期限管理）の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "task_add":
                    return tasks.add_task(
                        tool_input["title"],
                        tool_input.get("due_date", ""),
                        tool_input.get("priority", "medium"),
                        tool_input.get("category", ""),
                    )
                case "task_complete":
                    return tasks.complete_task(tool_input["task_id"])
                case "task_delete":
                    return tasks.delete_task(tool_input["task_id"])
                case "task_list":
                    return tasks.list_tasks(
                        tool_input.get("status", "pending"),
                        tool_input.get("category", ""),
                    )
                case "task_update":
                    return tasks.update_task(
                        tool_input["task_id"],
                        tool_input.get("title", ""),
                        tool_input.get("priority", ""),
                        tool_input.get("due_date", ""),
                        tool_input.get("category", ""),
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
