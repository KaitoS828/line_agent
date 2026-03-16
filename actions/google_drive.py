import io
import json
import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent.parent / "token.json"


class DriveActions:
    def __init__(self):
        self.service = None

    def _get_service(self):
        if self.service:
            return self.service

        creds = None

        # 環境変数からトークンを読み込む（Railway等クラウド環境向け）
        token_json_str = os.environ.get("GOOGLE_TOKEN_JSON")
        if token_json_str:
            creds = Credentials.from_authorized_user_info(
                json.loads(token_json_str), SCOPES
            )
        elif TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(
                        "credentials.json が見つかりません。"
                        "Google Cloud Console から OAuth2 認証情報をダウンロードして "
                        "line-agent/credentials.json に配置し、python auth_drive.py を実行してください。"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)

            TOKEN_FILE.write_text(creds.to_json())

        self.service = build("drive", "v3", credentials=creds)
        return self.service

    def create_folder(self, name: str, parent_id: str = None) -> str:
        service = self._get_service()
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        folder = service.files().create(
            body=metadata, fields="id,name,webViewLink"
        ).execute()
        return (
            f"✅ Driveフォルダ作成: {folder['name']}\n"
            f"ID: {folder['id']}\n"
            f"URL: {folder.get('webViewLink', 'N/A')}"
        )

    def upload_file(
        self,
        local_path: str,
        drive_folder_id: str = None,
        drive_filename: str = None,
    ) -> str:
        service = self._get_service()
        local = Path(local_path)
        if not local.exists():
            return f"❌ ファイルが見つかりません: {local_path}"
        filename = drive_filename or local.name
        metadata = {"name": filename}
        if drive_folder_id:
            metadata["parents"] = [drive_folder_id]
        media = MediaFileUpload(str(local), resumable=True)
        file = service.files().create(
            body=metadata, media_body=media, fields="id,name,webViewLink"
        ).execute()
        return (
            f"✅ アップロード完了: {file['name']}\n"
            f"ID: {file['id']}\n"
            f"URL: {file.get('webViewLink', 'N/A')}"
        )

    def create_file(
        self,
        name: str,
        content: str,
        folder_id: str = None,
        mime_type: str = "text/plain",
    ) -> str:
        service = self._get_service()
        metadata = {"name": name}
        if folder_id:
            metadata["parents"] = [folder_id]
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype=mime_type,
            resumable=False,
        )
        file = service.files().create(
            body=metadata, media_body=media, fields="id,name,webViewLink"
        ).execute()
        return (
            f"✅ Driveファイル作成: {file['name']}\n"
            f"ID: {file['id']}\n"
            f"URL: {file.get('webViewLink', 'N/A')}"
        )

    def list_files(self, folder_id: str = None, query: str = None) -> str:
        service = self._get_service()
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.insert(0, f"'{folder_id}' in parents")
        if query:
            q_parts.insert(0, f"name contains '{query}'")
        results = service.files().list(
            q=" and ".join(q_parts),
            pageSize=20,
            fields="files(id, name, mimeType, webViewLink)",
        ).execute()
        files = results.get("files", [])
        if not files:
            return "ファイルが見つかりません"
        lines = []
        for f in files:
            icon = "📁" if f["mimeType"] == "application/vnd.google-apps.folder" else "📄"
            lines.append(f"{icon} {f['name']}\n   ID: {f['id']}")
        return "\n".join(lines)

    def read_file(self, file_id: str) -> str:
        service = self._get_service()
        meta = service.files().get(
            fileId=file_id, fields="name,mimeType,webViewLink"
        ).execute()
        mime = meta.get("mimeType", "")
        if "google-apps" in mime:
            if "document" in mime:
                export_mime = "text/plain"
            elif "spreadsheet" in mime:
                export_mime = "text/csv"
            else:
                return (
                    f"📄 {meta['name']}\n"
                    f"URL: {meta.get('webViewLink', 'N/A')}\n"
                    "(バイナリ/非テキストファイルのため内容表示不可)"
                )
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        content = fh.getvalue().decode("utf-8", errors="replace")
        snippet = content[:5000] + ("...(省略)" if len(content) > 5000 else "")
        return f"📄 {meta['name']}\n---\n{snippet}"

    def edit_file(self, file_id: str, content: str) -> str:
        service = self._get_service()
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype="text/plain",
            resumable=False,
        )
        file = service.files().update(
            fileId=file_id, media_body=media, fields="id,name"
        ).execute()
        return f"✅ Driveファイル更新完了: {file['name']} (ID: {file['id']})"
