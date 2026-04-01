"""Google Drive管理担当エージェント — ファイルのアップロード・作成・読み書き"""

from actions.google_drive import DriveActions
from agents.base import BaseAgent
from agents.transcriber import TranscriberAgent

TOOLS = [
    {"name": "drive_create_folder", "description": "Google Driveにフォルダを作成", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "parent_id": {"type": "string"}}, "required": ["name"]}},
    {"name": "drive_upload_file", "description": "ローカルファイルをGoogle Driveにアップロード", "input_schema": {"type": "object", "properties": {"local_path": {"type": "string"}, "drive_folder_id": {"type": "string"}, "drive_filename": {"type": "string"}}, "required": ["local_path"]}},
    {"name": "drive_create_file", "description": "Google Driveにファイルを作成", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}, "folder_id": {"type": "string"}, "mime_type": {"type": "string"}}, "required": ["name", "content"]}},
    {"name": "drive_list_files", "description": "Google Driveのファイル一覧", "input_schema": {"type": "object", "properties": {"folder_id": {"type": "string"}, "query": {"type": "string"}}}},
    {"name": "drive_read_file", "description": "Google DriveのファイルURLや内容を取得", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]}},
    {"name": "drive_edit_file", "description": "Google Driveのファイルを更新", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_id", "content"]}},
    {"name": "drive_transcribe_audio", "description": "Google Driveの音声ファイル（m4a/mp3/wav等）をダウンロードしてWhisperで文字起こし・議事録を作成する", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string", "description": "DriveのファイルID"}, "filename": {"type": "string", "description": "ファイル名（検索用、file_idがない場合）"}}, "required": []}},
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
        self._transcriber = TranscriberAgent()

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "drive_create_folder": return self.drive.create_folder(tool_input["name"], tool_input.get("parent_id"))
                case "drive_upload_file": return self.drive.upload_file(tool_input["local_path"], tool_input.get("drive_folder_id"), tool_input.get("drive_filename"))
                case "drive_create_file": return self.drive.create_file(tool_input["name"], tool_input["content"], tool_input.get("folder_id"), tool_input.get("mime_type", "text/plain"))
                case "drive_list_files": return self.drive.list_files(tool_input.get("folder_id"), tool_input.get("query"))
                case "drive_read_file": return self.drive.read_file(tool_input["file_id"])
                case "drive_edit_file": return self.drive.edit_file(tool_input["file_id"], tool_input["content"])
                case "drive_transcribe_audio": return self._transcribe_audio(tool_input.get("file_id"), tool_input.get("filename"))
                case _: return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"

    def _transcribe_audio(self, file_id: str = None, filename: str = None) -> str:
        """DriveのオーディオファイルをダウンロードしてWhisperで文字起こし"""
        try:
            # file_idがなければファイル名で検索
            if not file_id and filename:
                results = self.drive.service.files().list(
                    q=f"name contains '{filename}'",
                    fields="files(id, name)",
                    pageSize=5,
                ).execute()
                files = results.get("files", [])
                if not files:
                    return f"❌ 「{filename}」というファイルが見つかりませんでした"
                file_id = files[0]["id"]
                filename = files[0]["name"]

            if not file_id:
                return "❌ file_idかfilenameを指定してください"

            # バイナリダウンロード
            request = self.drive.service.files().get_media(fileId=file_id)
            audio_data = request.execute()

            # Whisper文字起こし + 議事録
            return self._transcriber.transcribe(audio_data)
        except Exception as e:
            return f"❌ 音声文字起こしエラー: {e}"
