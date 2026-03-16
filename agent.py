import anthropic
from actions.computer import ComputerActions
from actions.google_drive import DriveActions

BASE_DIR = "/Users/sekimotokaito"

SYSTEM_PROMPT = f"""あなたはLINEを通じてユーザーのMac（{BASE_DIR}）を操作するAIアシスタントです。
Claude Codeのように、自然言語の指示を理解して適切なツールを使い、タスクを完了してください。

## ベースディレクトリ
{BASE_DIR}
- 相対パスが指定された場合は {BASE_DIR}/ を基準にしてください
- 新しいプロジェクトは {BASE_DIR}/<プロジェクト名>/ に作成します

## できること
- ローカル: フォルダ・ファイルの作成・読み取り・編集・一覧表示
- ローカル: シェルコマンドの実行（git init, npm install, python, brew など）
- Google Drive: フォルダ・ファイルの作成・アップロード・読み取り・編集・一覧表示

## 返答スタイル
- 日本語で簡潔に報告する
- 実行した内容と結果を箇条書きでまとめる
- エラーが発生した場合は原因と対処法を説明する
- IDやURLなど重要な情報は必ず含める"""

TOOLS = [
    {
        "name": "create_folder",
        "description": "ローカルマシンにフォルダ（ディレクトリ）を作成します",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "作成するフォルダのパス（絶対パスまたはベースディレクトリからの相対パス）",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_file",
        "description": "ローカルマシンにファイルを作成します",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "作成するファイルのパス"},
                "content": {"type": "string", "description": "ファイルの内容"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "ローカルマシンのファイルを読み込みます",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "読み込むファイルのパス"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "edit_file",
        "description": "ローカルマシンのファイルを編集します",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "編集するファイルのパス"},
                "content": {"type": "string", "description": "新しいファイルの内容"},
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "overwrite: 上書き, append: 追記（デフォルト: overwrite）",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "ディレクトリの内容を一覧表示します",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "一覧表示するディレクトリのパス",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_command",
        "description": "シェルコマンドを実行します（git, npm, python, brew など）",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "実行するシェルコマンド"},
                "cwd": {
                    "type": "string",
                    "description": "作業ディレクトリ（省略時はベースディレクトリ）",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "drive_create_folder",
        "description": "Google Driveにフォルダを作成します",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "フォルダ名"},
                "parent_id": {
                    "type": "string",
                    "description": "親フォルダのID（省略時はルート）",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "drive_upload_file",
        "description": "ローカルファイルをGoogle Driveにアップロードします",
        "input_schema": {
            "type": "object",
            "properties": {
                "local_path": {
                    "type": "string",
                    "description": "アップロードするローカルファイルのパス",
                },
                "drive_folder_id": {
                    "type": "string",
                    "description": "アップロード先のDriveフォルダID（省略時はルート）",
                },
                "drive_filename": {
                    "type": "string",
                    "description": "Drive上でのファイル名（省略時はローカルのファイル名）",
                },
            },
            "required": ["local_path"],
        },
    },
    {
        "name": "drive_create_file",
        "description": "Google Driveに新しいファイルを作成します（内容を直接指定）",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "ファイル名"},
                "content": {"type": "string", "description": "ファイルの内容"},
                "folder_id": {
                    "type": "string",
                    "description": "保存先フォルダのID（省略時はルート）",
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIMEタイプ（例: text/plain, text/html）",
                },
            },
            "required": ["name", "content"],
        },
    },
    {
        "name": "drive_list_files",
        "description": "Google Driveのファイル・フォルダ一覧を表示します",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "description": "一覧表示するフォルダのID（省略時はルート）",
                },
                "query": {
                    "type": "string",
                    "description": "ファイル名の検索キーワード",
                },
            },
        },
    },
    {
        "name": "drive_read_file",
        "description": "Google DriveのファイルのURLや内容を取得します",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ファイルのID"}
            },
            "required": ["file_id"],
        },
    },
    {
        "name": "drive_edit_file",
        "description": "Google Driveの既存ファイルの内容を更新します",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "編集するファイルのID",
                },
                "content": {
                    "type": "string",
                    "description": "新しいファイルの内容",
                },
            },
            "required": ["file_id", "content"],
        },
    },
]


class LineAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.computer = ComputerActions(BASE_DIR)
        self.drive = DriveActions()

    def run(self, user_message: str) -> str:
        messages = [{"role": "user", "content": user_message}]

        # ツールループ（最大10回）
        for _ in range(10):
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return "✅ 完了しました。"

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result),
                            }
                        )
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return "✅ 処理が完了しました。"

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "create_folder":
                    return self.computer.create_folder(tool_input["path"])
                case "create_file":
                    return self.computer.create_file(
                        tool_input["path"], tool_input["content"]
                    )
                case "read_file":
                    return self.computer.read_file(tool_input["path"])
                case "edit_file":
                    return self.computer.edit_file(
                        tool_input["path"],
                        tool_input["content"],
                        tool_input.get("mode", "overwrite"),
                    )
                case "list_directory":
                    return self.computer.list_directory(tool_input["path"])
                case "run_command":
                    return self.computer.run_command(
                        tool_input["command"], tool_input.get("cwd")
                    )
                case "drive_create_folder":
                    return self.drive.create_folder(
                        tool_input["name"], tool_input.get("parent_id")
                    )
                case "drive_upload_file":
                    return self.drive.upload_file(
                        tool_input["local_path"],
                        tool_input.get("drive_folder_id"),
                        tool_input.get("drive_filename"),
                    )
                case "drive_create_file":
                    return self.drive.create_file(
                        tool_input["name"],
                        tool_input["content"],
                        tool_input.get("folder_id"),
                        tool_input.get("mime_type", "text/plain"),
                    )
                case "drive_list_files":
                    return self.drive.list_files(
                        tool_input.get("folder_id"), tool_input.get("query")
                    )
                case "drive_read_file":
                    return self.drive.read_file(tool_input["file_id"])
                case "drive_edit_file":
                    return self.drive.edit_file(
                        tool_input["file_id"], tool_input["content"]
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {str(e)}"
