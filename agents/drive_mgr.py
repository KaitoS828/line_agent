"""Google Drive管理担当エージェント — ファイルのアップロード・作成・読み書き"""

from actions.google_drive import DriveActions
from agents.base import BaseAgent

TOOLS = [
    {"name": "drive_create_folder", "description": "Google Driveにフォルダを作成", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "parent_id": {"type": "string"}}, "required": ["name"]}},
    {"name": "drive_upload_file", "description": "ローカルファイルをGoogle Driveにアップロード", "input_schema": {"type": "object", "properties": {"local_path": {"type": "string"}, "drive_folder_id": {"type": "string"}, "drive_filename": {"type": "string"}}, "required": ["local_path"]}},
    {"name": "drive_create_file", "description": "Google Driveにファイルを作成", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}, "folder_id": {"type": "string"}, "mime_type": {"type": "string"}}, "required": ["name", "content"]}},
    {"name": "drive_list_files", "description": "Google Driveのファイル一覧", "input_schema": {"type": "object", "properties": {"folder_id": {"type": "string"}, "query": {"type": "string"}}}},
    {"name": "drive_read_file", "description": "Google DriveのファイルURLや内容を取得", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]}},
    {"name": "drive_edit_file", "description": "Google Driveのファイルを更新", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_id", "content"]}},
]

SYSTEM_PROMPT = """あなたはGoogle Drive管理の専門家です。
ファイルのアップロード・作成・読み書き・フォルダ管理を担当します。

## 得意分野
- ファイル・フォルダの作成と整理
- ローカルファイルのアップロード
- Driveファイルの読み取り・更新
- ファイル検索

## ルール
- 日本語で簡潔に結果を報告する
- ファイルIDやURLを含めて報告する
- エラーが出た場合は原因と対処法を説明する"""


class DriveMgrAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="DriveMgrAgent",
            role="Google Driveのファイル・フォルダ管理の専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )
        self.drive = DriveActions(creds)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "drive_create_folder": return self.drive.create_folder(tool_input["name"], tool_input.get("parent_id"))
                case "drive_upload_file": return self.drive.upload_file(tool_input["local_path"], tool_input.get("drive_folder_id"), tool_input.get("drive_filename"))
                case "drive_create_file": return self.drive.create_file(tool_input["name"], tool_input["content"], tool_input.get("folder_id"), tool_input.get("mime_type", "text/plain"))
                case "drive_list_files": return self.drive.list_files(tool_input.get("folder_id"), tool_input.get("query"))
                case "drive_read_file": return self.drive.read_file(tool_input["file_id"])
                case "drive_edit_file": return self.drive.edit_file(tool_input["file_id"], tool_input["content"])
                case _: return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
