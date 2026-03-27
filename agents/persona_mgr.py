"""キャラ管理担当エージェント — カスタムプロンプトの追加・削除・一覧"""

from actions.custom_prompt import (
    set_custom_instruction,
    list_custom_instructions,
    clear_custom_instructions,
    remove_custom_instruction,
)
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "add_instruction",
        "description": "カスタム指示を追加する（例: もっとフランクに話して、敬語を使って）",
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "追加する指示内容"},
            },
            "required": ["instruction"],
        },
    },
    {
        "name": "list_instructions",
        "description": "現在のカスタム指示一覧を表示",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "remove_instruction",
        "description": "指定番号のカスタム指示を削除",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "削除する指示の番号"},
            },
            "required": ["index"],
        },
    },
    {
        "name": "clear_instructions",
        "description": "カスタム指示を全てクリア",
        "input_schema": {"type": "object", "properties": {}},
    },
]

SYSTEM_PROMPT = """あなたはキャラクター設定の管理担当です。
ユーザーからの指示に従って、AIアシスタントのキャラや口調のカスタム設定を管理します。

## ルール
- ユーザーが口調や話し方の変更を望んでいる場合はadd_instructionを使う
- 「設定見せて」「今の設定は？」にはlist_instructionsを使う
- 「設定リセット」「全部消して」にはclear_instructionsを使う
- 特定の番号を消したい場合はremove_instructionを使う
- タスク内にuser_id:が含まれている場合はそのIDを使用する"""


class PersonaMgrAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="PersonaMgrAgent",
            role="キャラ設定・口調カスタマイズの管理。「もっと丁寧に話して」「敬語やめて」「設定見せて」「設定リセット」に対応",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self._user_id = "default"

    def run(self, task: str) -> str:
        # Extract user_id if provided
        if "user_id:" in task:
            parts = task.split("user_id:", 1)
            self._user_id = parts[1].split("\n")[0].strip()
            task = parts[0].strip()
        return super().run(task)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "add_instruction":
                    return set_custom_instruction(self._user_id, tool_input["instruction"])
                case "list_instructions":
                    return list_custom_instructions(self._user_id)
                case "remove_instruction":
                    return remove_custom_instruction(self._user_id, tool_input["index"])
                case "clear_instructions":
                    return clear_custom_instructions(self._user_id)
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
