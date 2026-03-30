"""Notion連携アクション — ページ作成・読み取り・DB操作"""

import httpx
from config import NOTION_API_KEY, NOTION_DATABASE_ID

BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def _get(path: str, params: dict = None) -> dict:
    resp = httpx.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, data: dict) -> dict:
    resp = httpx.post(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, data: dict) -> dict:
    resp = httpx.patch(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=20)
    resp.raise_for_status()
    return resp.json()


# ── ページ作成 ─────────────────────────────────────────────────

def create_page(title: str, content: str, parent_page_id: str = None) -> str:
    """Notionにページを作成してURLを返す"""
    if not NOTION_API_KEY:
        return "❌ NOTION_API_KEY が設定されていません"

    # 親: DBがあればDB、なければページ指定、なければワークスペース
    if NOTION_DATABASE_ID:
        parent = {"database_id": NOTION_DATABASE_ID}
        properties = {
            "Name": {"title": [{"text": {"content": title}}]}
        }
    elif parent_page_id:
        parent = {"page_id": parent_page_id}
        properties = {
            "title": [{"text": {"content": title}}]
        }
    else:
        return "❌ NOTION_DATABASE_ID または 親ページIDが必要です"

    # 本文をNotionブロックに変換
    blocks = _text_to_blocks(content)

    try:
        result = _post("/pages", {
            "parent": parent,
            "properties": properties,
            "children": blocks,
        })
        page_url = result.get("url", "")
        page_id = result.get("id", "")
        return f"ページ作ったよ！\n{page_url}"
    except httpx.HTTPStatusError as e:
        return f"❌ Notion APIエラー ({e.response.status_code}): {e.response.text[:300]}"
    except Exception as e:
        return f"❌ ページ作成エラー: {e}"


def read_page(page_id: str) -> str:
    """NotionページのテキストをMarkdown風に取得"""
    if not NOTION_API_KEY:
        return "❌ NOTION_API_KEY が設定されていません"
    try:
        blocks = _get(f"/blocks/{page_id}/children", {"page_size": 100})
        lines = []
        for block in blocks.get("results", []):
            text = _block_to_text(block)
            if text:
                lines.append(text)
        return "\n".join(lines) if lines else "（空のページ）"
    except Exception as e:
        return f"❌ ページ読み取りエラー: {e}"


def search_pages(query: str, max_results: int = 5) -> str:
    """Notionをキーワード検索"""
    if not NOTION_API_KEY:
        return "❌ NOTION_API_KEY が設定されていません"
    try:
        result = _post("/search", {
            "query": query,
            "page_size": max_results,
            "filter": {"value": "page", "property": "object"},
        })
        pages = result.get("results", [])
        if not pages:
            return "該当するページが見つかりませんでした"

        lines = []
        for p in pages:
            title = _get_page_title(p)
            url = p.get("url", "")
            lines.append(f"・ {title}\n  {url}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 検索エラー: {e}"


def list_db_pages(max_results: int = 10) -> str:
    """データベースのページ一覧を取得"""
    if not NOTION_API_KEY:
        return "❌ NOTION_API_KEY が設定されていません"
    if not NOTION_DATABASE_ID:
        return "❌ NOTION_DATABASE_ID が設定されていません"
    try:
        result = _post(f"/databases/{NOTION_DATABASE_ID}/query", {
            "page_size": max_results,
        })
        pages = result.get("results", [])
        if not pages:
            return "データベースにページがありません"

        lines = []
        for p in pages:
            title = _get_page_title(p)
            url = p.get("url", "")
            lines.append(f"・ {title}\n  {url}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ DB読み取りエラー: {e}"


def append_to_page(page_id: str, content: str) -> str:
    """既存ページに内容を追記"""
    if not NOTION_API_KEY:
        return "❌ NOTION_API_KEY が設定されていません"
    try:
        blocks = _text_to_blocks(content)
        _patch(f"/blocks/{page_id}/children", {"children": blocks})
        return "追記したよ！"
    except Exception as e:
        return f"❌ 追記エラー: {e}"


# ── ヘルパー ───────────────────────────────────────────────────

def _text_to_blocks(text: str) -> list:
    """テキストをNotionブロックのリストに変換"""
    blocks = []
    for line in text.split("\n"):
        if not line.strip():
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": []}})
            continue
        # 見出し
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})
        # 箇条書き
        elif line.startswith("- ") or line.startswith("・ "):
            content = line[2:]
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}})
        # 通常テキスト（2000文字制限対応）
        else:
            for chunk in [line[i:i+2000] for i in range(0, len(line), 2000)]:
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}})
    return blocks[:100]  # Notionは1リクエスト100ブロックまで


def _block_to_text(block: dict) -> str:
    """Notionブロックからテキストを抽出"""
    btype = block.get("type", "")
    data = block.get(btype, {})
    rich_text = data.get("rich_text", [])
    text = "".join(rt.get("plain_text", "") for rt in rich_text)

    if btype == "heading_1":
        return f"# {text}"
    elif btype == "heading_2":
        return f"## {text}"
    elif btype == "heading_3":
        return f"### {text}"
    elif btype == "bulleted_list_item":
        return f"・ {text}"
    elif btype == "numbered_list_item":
        return f"1. {text}"
    elif btype == "to_do":
        checked = "✅" if data.get("checked") else "☐"
        return f"{checked} {text}"
    elif btype == "divider":
        return "---"
    return text


def _get_page_title(page: dict) -> str:
    """ページオブジェクトからタイトルを取得"""
    props = page.get("properties", {})
    for key in ["Name", "title", "Title", "名前"]:
        if key in props:
            title_data = props[key]
            if title_data.get("type") == "title":
                rich = title_data.get("title", [])
                return "".join(r.get("plain_text", "") for r in rich) or "（無題）"
    return "（無題）"
