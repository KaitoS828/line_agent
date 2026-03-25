import json
import os
from pathlib import Path

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from actions.computer import ComputerActions
from actions.google_drive import DriveActions
from actions.calendar import CalendarActions
from actions.sheets import SheetsActions

BASE_DIR = "/Users/sekimotokaito"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_google_creds() -> Credentials:
    creds = None
    token_json_str = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json_str:
        creds = Credentials.from_authorized_user_info(json.loads(token_json_str), SCOPES)
    elif TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if TOKEN_FILE.exists():
                TOKEN_FILE.write_text(creds.to_json())
        else:
            raise RuntimeError("Google認証が必要です。python auth_drive.py を実行してください。")
    return creds


# ── 各専門エージェントのツール定義 ──────────────────────────────

COMPUTER_TOOLS = [
    {"name": "create_folder", "description": "ローカルにフォルダを作成", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "create_file", "description": "ローカルにファイルを作成", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "read_file", "description": "ローカルのファイルを読み込む", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "edit_file", "description": "ローカルのファイルを編集", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "mode": {"type": "string", "enum": ["overwrite", "append"]}}, "required": ["path", "content"]}},
    {"name": "list_directory", "description": "ディレクトリ一覧を表示", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "run_command", "description": "シェルコマンドを実行（git, npm, python, brew など）", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}}, "required": ["command"]}},
]

DRIVE_TOOLS = [
    {"name": "drive_create_folder", "description": "Google Driveにフォルダを作成", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "parent_id": {"type": "string"}}, "required": ["name"]}},
    {"name": "drive_upload_file", "description": "ローカルファイルをGoogle Driveにアップロード", "input_schema": {"type": "object", "properties": {"local_path": {"type": "string"}, "drive_folder_id": {"type": "string"}, "drive_filename": {"type": "string"}}, "required": ["local_path"]}},
    {"name": "drive_create_file", "description": "Google Driveにファイルを作成", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}, "folder_id": {"type": "string"}, "mime_type": {"type": "string"}}, "required": ["name", "content"]}},
    {"name": "drive_list_files", "description": "Google Driveのファイル一覧", "input_schema": {"type": "object", "properties": {"folder_id": {"type": "string"}, "query": {"type": "string"}}}},
    {"name": "drive_read_file", "description": "Google DriveのファイルURLや内容を取得", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]}},
    {"name": "drive_edit_file", "description": "Google Driveのファイルを更新", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_id", "content"]}},
]

CALENDAR_TOOLS = [
    {"name": "calendar_list_events", "description": "Googleカレンダーの予定一覧を取得", "input_schema": {"type": "object", "properties": {"max_results": {"type": "integer"}, "calendar_id": {"type": "string"}}}},
    {"name": "calendar_create_event", "description": "Googleカレンダーに予定を作成", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "start": {"type": "string", "description": "ISO8601形式 例: 2026-03-17T10:00:00+09:00"}, "end": {"type": "string"}, "description": {"type": "string"}, "calendar_id": {"type": "string"}}, "required": ["title", "start", "end"]}},
    {"name": "calendar_update_event", "description": "Googleカレンダーの予定を更新", "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "title": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}, "description": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "calendar_delete_event", "description": "Googleカレンダーの予定を削除", "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "calendar_search_events", "description": "Googleカレンダーの予定を検索", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]

SHEETS_TOOLS = [
    {"name": "sheets_create", "description": "Googleスプレッドシートを新規作成", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "sheets_read", "description": "スプレッドシートのデータを読み込む", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}}, "required": ["spreadsheet_id"]}},
    {"name": "sheets_write", "description": "スプレッドシートにデータを書き込む", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}, "values": {"type": "array"}}, "required": ["spreadsheet_id", "range", "values"]}},
    {"name": "sheets_append", "description": "スプレッドシートにデータを追記する", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}, "values": {"type": "array"}}, "required": ["spreadsheet_id", "range", "values"]}},
    {"name": "sheets_list_sheets", "description": "スプレッドシートのシート一覧を取得", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}}, "required": ["spreadsheet_id"]}},
    {"name": "sheets_add_sheet", "description": "スプレッドシートにシートを追加", "input_schema": {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "sheet_name": {"type": "string"}}, "required": ["spreadsheet_id", "sheet_name"]}},
]

# ── 専門エージェント基底クラス ───────────────────────────────────

class BaseAgent:
    def __init__(self, name: str, system_prompt: str, tools: list):
        self.client = anthropic.Anthropic()
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools

    def run(self, task: str) -> str:
        messages = [{"role": "user", "content": task}]
        for _ in range(10):
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
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
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(result)})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        return "✅ 処理が完了しました。"

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        raise NotImplementedError


# ── 専門エージェント ─────────────────────────────────────────────

class ComputerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ComputerAgent",
            system_prompt=f"あなたはローカルPC（{BASE_DIR}）のファイル操作とコマンド実行の専門家です。日本語で簡潔に結果を報告してください。",
            tools=COMPUTER_TOOLS,
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
            return f"❌ {tool_name} エラー: {str(e)}"


class DriveAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="DriveAgent",
            system_prompt="あなたはGoogle Drive操作の専門家です。ファイルのアップロード・作成・読み書き・一覧表示を担当します。日本語で簡潔に結果を報告してください。",
            tools=DRIVE_TOOLS,
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
            return f"❌ {tool_name} エラー: {str(e)}"


class CalendarAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="CalendarAgent",
            system_prompt="あなたはGoogleカレンダー操作の専門家です。予定の作成・確認・更新・削除を担当します。日本語で簡潔に結果を報告してください。日時はAsia/Tokyoタイムゾーンで扱ってください。",
            tools=CALENDAR_TOOLS,
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
            return f"❌ {tool_name} エラー: {str(e)}"


class SheetsAgent(BaseAgent):
    def __init__(self, creds):
        super().__init__(
            name="SheetsAgent",
            system_prompt="あなたはGoogleスプレッドシート操作の専門家です。スプレッドシートの作成・読み書き・編集を担当します。日本語で簡潔に結果を報告してください。",
            tools=SHEETS_TOOLS,
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
            return f"❌ {tool_name} エラー: {str(e)}"


# ── OrchestratorAgent（司令塔） ──────────────────────────────────

ORCHESTRATOR_TOOLS = [
    {
        "name": "delegate_to_agent",
        "description": "専門エージェントにタスクを委譲する",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": ["computer", "drive", "calendar", "sheets"],
                    "description": "computer: ローカルPC操作, drive: Google Drive, calendar: Googleカレンダー, sheets: Googleスプレッドシート",
                },
                "task": {
                    "type": "string",
                    "description": "エージェントに渡すタスクの詳細な指示",
                },
            },
            "required": ["agent", "task"],
        },
    }
]

ORCHESTRATOR_PROMPT = f"""あなたはLINEを通じてユーザーの指示を受け取るオーケストレーター（司令塔）AIです。
ユーザーの指示を理解し、適切な専門エージェントにタスクを委譲してください。

## 専門エージェント
- computer: ローカルPC（{BASE_DIR}）のファイル操作・コマンド実行
- drive: Google Driveのファイル・フォルダ管理
- calendar: Googleカレンダーの予定管理
- sheets: Googleスプレッドシートの作成・読み書き

## ルール
- 1つのリクエストで複数のエージェントへの委譲が可能
- タスクが複数のエージェントにまたがる場合は順番に委譲する
- 最終的な結果を日本語で簡潔にまとめてユーザーに返す
- エラーが発生した場合は原因と対処法を説明する"""


IMAGE_ANALYSIS_PROMPT = """あなたはLINEで送られてきた画像を分析するAIアシスタントです。
画像の内容を日本語で分かりやすく説明してください。

以下のような分析を行ってください：
- 画像に何が写っているかの説明
- テキストが含まれている場合はOCR（文字起こし）
- レシートや請求書の場合は金額や店名などの要点を抽出
- 名刺の場合は連絡先情報を整理
- スクリーンショットの場合は内容の要約
- 料理の写真の場合は料理名の推測やカロリーの概算
- その他、画像から読み取れる有用な情報

簡潔かつ実用的に回答してください。"""


class LineAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        creds = get_google_creds()
        self.agents = {
            "computer": ComputerAgent(),
            "drive": DriveAgent(creds),
            "calendar": CalendarAgent(creds),
            "sheets": SheetsAgent(creds),
        }

    def run(self, user_message: str) -> str:
        messages = [{"role": "user", "content": user_message}]
        for _ in range(10):
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=ORCHESTRATOR_PROMPT,
                tools=ORCHESTRATOR_TOOLS,
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
                        result = self._delegate(block.input["agent"], block.input["task"])
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        return "✅ 処理が完了しました。"

    def run_with_image(self, image_b64: str) -> str:
        """画像を分析して結果を返す"""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "この画像を分析してください。",
                    },
                ],
            }
        ]
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=IMAGE_ANALYSIS_PROMPT,
            messages=messages,
        )
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "画像を確認しましたが、特にコメントはありません。"

    def _delegate(self, agent_name: str, task: str) -> str:
        agent = self.agents.get(agent_name)
        if not agent:
            return f"❌ 未知のエージェント: {agent_name}"
        return agent.run(task)
