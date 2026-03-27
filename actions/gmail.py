"""Gmail アクション — メールの送受信・検索"""

import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build


class GmailActions:
    def __init__(self, creds):
        self.service = build("gmail", "v1", credentials=creds)

    def send_email(self, to: str, subject: str, body: str) -> str:
        """メールを送信する"""
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        result = self.service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return f"✅ メール送信完了 (ID: {result['id']})\n宛先: {to}\n件名: {subject}"

    def search_emails(self, query: str, max_results: int = 10) -> str:
        """メールを検索する"""
        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            return "該当するメールが見つかりませんでした。"

        lines = []
        for msg_info in messages[:max_results]:
            msg = self.service.users().messages().get(
                userId="me", id=msg_info["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            lines.append(
                f"• [{headers.get('Date', '不明')}] {headers.get('From', '不明')}\n"
                f"  件名: {headers.get('Subject', '(なし)')}\n"
                f"  ID: {msg_info['id']}"
            )
        return "\n\n".join(lines)

    def read_email(self, message_id: str) -> str:
        """メールの本文を読む"""
        msg = self.service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

        # 本文を取得
        body = self._extract_body(msg.get("payload", {}))

        return (
            f"📧 メール詳細\n"
            f"From: {headers.get('From', '不明')}\n"
            f"To: {headers.get('To', '不明')}\n"
            f"Date: {headers.get('Date', '不明')}\n"
            f"Subject: {headers.get('Subject', '(なし)')}\n\n"
            f"{body}"
        )

    def list_unread(self, max_results: int = 10) -> str:
        """未読メール一覧を取得"""
        return self.search_emails("is:unread", max_results)

    def _extract_body(self, payload: dict) -> str:
        """メール本文をペイロードから抽出"""
        # シンプルなメール
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        # マルチパート
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

        # フォールバック: HTMLからテキスト部分
        for part in payload.get("parts", []):
            if part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")[:2000]

        return "(本文を取得できませんでした)"
