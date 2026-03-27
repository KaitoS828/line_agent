"""レポート生成アクション — Web調査 → レポート作成 → Google Docs → PDF"""

import io

import anthropic
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from config import ANTHROPIC_API_KEY
from actions import web_search


def research_topic(query: str, max_results: int = 5) -> str:
    """トピックをWeb検索して情報を収集"""
    return web_search.search(query, max_results=max_results)


def generate_report(topic: str, research_data: str) -> str:
    """収集した情報からレポートを生成"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system="""あなたはプロのリサーチャー兼レポートライターです。
収集された情報を元に、構造化されたレポートを日本語で作成してください。

## レポートフォーマット
# [タイトル]

## 概要
（2-3文の要約）

## 主な調査結果
### 1. [ポイント1]
（詳細）

### 2. [ポイント2]
（詳細）

### 3. [ポイント3]
（詳細）

## まとめ・所感
（全体のまとめと今後の展望）

## 参考リンク
- [ソース1のURL]
- [ソース2のURL]

---
作成日: [日付]

## ルール
- 事実に基づいた内容にする
- 不確かな情報は「未確認」と明記
- 箇条書きと見出しで読みやすく構造化
- 参考リンクを必ず含める""",
        messages=[{
            "role": "user",
            "content": f"以下のトピックについてレポートを作成してください。\n\nトピック: {topic}\n\n収集された情報:\n{research_data}",
        }],
    )

    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def save_as_google_doc(drive_service, title: str, content: str, folder_id: str = None) -> dict:
    """レポートをGoogle Docsとして保存"""
    metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
    }
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")),
        mimetype="text/plain",
        resumable=False,
    )
    doc = drive_service.files().create(
        body=metadata, media_body=media, fields="id,name,webViewLink"
    ).execute()
    return doc


def export_as_pdf(drive_service, file_id: str) -> bytes:
    """Google DocsをPDFにエクスポート"""
    request = drive_service.files().export_media(
        fileId=file_id, mimeType="application/pdf"
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()


def upload_pdf(drive_service, pdf_data: bytes, title: str, folder_id: str = None) -> dict:
    """PDFをDriveにアップロード"""
    metadata = {"name": f"{title}.pdf"}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_data),
        mimetype="application/pdf",
        resumable=False,
    )
    pdf_file = drive_service.files().create(
        body=metadata, media_body=media, fields="id,name,webViewLink"
    ).execute()
    return pdf_file


def create_report_pipeline(drive_service, topic: str, folder_id: str = None) -> str:
    """調査 → レポート生成 → Google Docs保存 → PDF変換 → リンク返却"""
    # 1. Web検索で情報収集
    research_data = research_topic(topic)
    if not research_data:
        return "❌ 情報を収集できませんでした"

    # 2. レポート生成
    report_content = generate_report(topic, research_data)
    if not report_content:
        return "❌ レポートを生成できませんでした"

    # 3. Google Docsとして保存
    doc = save_as_google_doc(drive_service, f"レポート: {topic}", report_content, folder_id)

    # 4. PDF変換
    pdf_data = export_as_pdf(drive_service, doc["id"])

    # 5. PDFをDriveにアップロード
    pdf_file = upload_pdf(drive_service, pdf_data, f"レポート_{topic}", folder_id)

    return (
        f"✅ レポート作成完了！\n\n"
        f"📄 Google Docs:\n{doc.get('webViewLink', 'N/A')}\n\n"
        f"📑 PDF:\n{pdf_file.get('webViewLink', 'N/A')}"
    )
