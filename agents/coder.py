"""コーディング担当エージェント — ファイル操作・コマンド実行"""

from actions.computer import ComputerActions
from agents.base import BaseAgent

BASE_DIR = "/Users/sekimotokaito"

TOOLS = [
    {"name": "create_folder", "description": "ローカルにフォルダを作成", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "create_file", "description": "ローカルにファイルを作成", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "read_file", "description": "ローカルのファイルを読み込む", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "edit_file", "description": "ローカルのファイルを編集", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "mode": {"type": "string", "enum": ["overwrite", "append"]}}, "required": ["path", "content"]}},
    {"name": "list_directory", "description": "ディレクトリ一覧を表示", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "run_command", "description": "シェルコマンドを実行（git, npm, python, brew など）", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}}, "required": ["command"]}},
]

SYSTEM_PROMPT = f"""あなたはコーディング・ファイル操作の専門家です。
ローカルPC（{BASE_DIR}）でのファイル作成・編集・コマンド実行を担当します。

## 得意分野
- プログラミング（Python, JavaScript, HTML/CSS など）
- ファイル・フォルダの作成・編集・整理
- git操作、npm/pip等のパッケージ管理
- シェルコマンドの実行

## ルール
- 結果を日本語で簡潔に報告する
- エラーが出た場合は原因と対処法を説明する
- コードを書く場合はベストプラクティスに従う"""


class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CoderAgent",
            role="コーディング・ファイル操作・コマンド実行の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self.computer = ComputerActions(BASE_DIR)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "create_folder": return self.computer.create_folder(tool_input["path"])
                case "create_file": return self.computer.create_file(tool_input["path"], tool_input["content"])
                case "read_file": return self.computer.read_file(tool_input["path"])
                case "edit_file": return self.computer.edit_file(tool_input["path"], tool_input["content"], tool_input.get("mode", "overwrite"))
                case "list_directory": return self.computer.list_directory(tool_input["path"])
                case "run_command": return self.computer.run_command(tool_input["command"], tool_input.get("cwd"))
                case _: return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
