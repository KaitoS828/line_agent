"""Notion管理エージェント — 記事保存・教材作成・ページ読み書き"""

import anthropic
from config import ANTHROPIC_API_KEY
from agents.base import BaseAgent
from actions import notion
from actions.url_extract import fetch_page_content

TOOLS = [
    {
        "name": "create_page",
        "description": "Notionに新しいページを作成する",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "ページタイトル"},
                "content": {"type": "string", "description": "ページ本文（Markdown形式可）"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "read_page",
        "description": "NotionページIDを指定してページ内容を読み取る",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "NotionページID（URLの末尾32文字）"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "search_pages",
        "description": "Notionをキーワード検索してページ一覧を返す",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_pages",
        "description": "Notionデータベースのページ一覧を取得する",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "最大件数（デフォルト10）"},
            },
        },
    },
    {
        "name": "append_to_page",
        "description": "既存のNotionページに内容を追記する",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "追記先NotionページID"},
                "content": {"type": "string", "description": "追記する内容"},
            },
            "required": ["page_id", "content"],
        },
    },
    {
        "name": "fetch_url_and_save",
        "description": "URLの記事内容を取得してNotionに保存する",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "保存したい記事のURL"},
                "title": {"type": "string", "description": "ページタイトル（省略時は記事タイトルを自動取得）"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "create_study_material",
        "description": "指定したテーマで学習教材をNotion上に自動作成する",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme": {"type": "string", "description": "教材のテーマ（例: 「AIエージェントの基礎」）"},
                "level": {"type": "string", "description": "難易度（初心者・中級者・上級者）", "default": "初心者"},
            },
            "required": ["theme"],
        },
    },
]

SYSTEM_PROMPT = """あなたはNotion管理の専門家です。
ユーザーの依頼に応じて、Notionへの記事保存・ページ作成・教材作成・検索を行います。

## 得意なこと
- URLの記事をNotionに保存（要約付き）
- テーマを指定して学習教材を自動生成
- Notionのページ検索・読み取り
- メモや議事録の保存

## ルール
- 日本語で簡潔に報告する
- ページ作成後は必ずURLを伝える
- 教材作成は目次→各セクションの構成で作る"""


class NotionMgrAgent(BaseAgent):
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        super().__init__(
            name="NotionMgrAgent",
            role="Notionへの記事保存・教材自動作成・ページ読み書きの専門家",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "create_page":
                    return notion.create_page(
                        tool_input["title"],
                        tool_input["content"],
                    )
                case "read_page":
                    return notion.read_page(tool_input["page_id"])
                case "search_pages":
                    return notion.search_pages(tool_input["query"])
                case "list_pages":
                    return notion.list_db_pages(tool_input.get("max_results", 10))
                case "append_to_page":
                    return notion.append_to_page(
                        tool_input["page_id"],
                        tool_input["content"],
                    )
                case "fetch_url_and_save":
                    return self._fetch_and_save(
                        tool_input["url"],
                        tool_input.get("title", ""),
                    )
                case "create_study_material":
                    return self._create_study_material(
                        tool_input["theme"],
                        tool_input.get("level", "初心者"),
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"

    def _fetch_and_save(self, url: str, title: str) -> str:
        """記事を取得してClaudeで要約しNotionに保存"""
        content = fetch_page_content(url, max_chars=4000)
        if "エラー" in content or "取得できませんでした" in content:
            return f"❌ 記事取得失敗: {content}"

        response = self.claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"""以下の記事を構造化してまとめてください。

出力フォーマット:
# 要約
（3行以内）

# 主なポイント
- ポイント1
- ポイント2
- ポイント3

# 詳細
（本文の重要部分を整理）

# 出典
{url}

---
記事内容:
{content}"""}],
        )
        summary = ""
        for block in response.content:
            if hasattr(block, "text"):
                summary = block.text
                break

        page_title = title or f"📎 {url[:50]}..."
        return notion.create_page(page_title, summary)

    def _create_study_material(self, theme: str, level: str) -> str:
        """テーマを受け取りClaudeで教材を生成してNotionに保存"""
        response = self.claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": f"""「{theme}」についての学習教材を{level}向けに作成してください。

## 構成
# {theme} — 学習教材（{level}向け）

## この教材で学べること
（3点箇条書き）

## 第1章: 基本概念
（説明）

## 第2章: 実践的な内容
（説明）

## 第3章: 応用・まとめ
（説明）

## 参考リソース
- （関連リンクや書籍など）

---
・わかりやすい日本語で書く
・具体例を必ず入れる
・{level}が理解できるレベルに調整する"""}],
        )
        material = ""
        for block in response.content:
            if hasattr(block, "text"):
                material = block.text
                break

        return notion.create_page(f"📚 {theme}（{level}向け教材）", material)
