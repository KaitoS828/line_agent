"""GitHub管理担当エージェント — リポジトリの status / commit / push"""

from actions import github_ops
from agents.base import BaseAgent

TOOLS = [
    {
        "name": "repo_status",
        "description": "現在ブランチと変更状態（git status）を確認する",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "commit_changes",
        "description": "変更をコミットする（必要に応じて未追跡ファイルも含む）",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "コミットメッセージ"},
                "include_untracked": {
                    "type": "boolean",
                    "description": "未追跡ファイルもコミット対象に含める（デフォルトtrue）",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "push_current_branch",
        "description": "現在のブランチを origin に push する",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "commit_and_push",
        "description": "変更をコミットして、そのまま push まで行う",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "コミットメッセージ"},
                "include_untracked": {
                    "type": "boolean",
                    "description": "未追跡ファイルもコミット対象に含める（デフォルトtrue）",
                },
            },
            "required": ["message"],
        },
    },
]

SYSTEM_PROMPT = """あなたはGitHub運用担当です。
ユーザーの指示に応じて、リポジトリ状態確認・コミット・pushを行います。

## ルール
- まずrepo_statusで状態を確認してから作業する
- コミット要求にはcommit_changesまたはcommit_and_pushを使う
- push要求にはpush_current_branchを使う
- エラー時は原因と次の手順を簡潔に伝える"""


class GithubMgrAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="GithubMgrAgent",
            role="GitHub操作（status/commit/push）の担当。「コミットして」「pushして」「状態見せて」に対応",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            match tool_name:
                case "repo_status":
                    return github_ops.repo_status()
                case "commit_changes":
                    return github_ops.commit_changes(
                        message=tool_input["message"],
                        include_untracked=tool_input.get("include_untracked", True),
                    )
                case "push_current_branch":
                    return github_ops.push_current_branch()
                case "commit_and_push":
                    return github_ops.commit_and_push(
                        message=tool_input["message"],
                        include_untracked=tool_input.get("include_untracked", True),
                    )
                case _:
                    return f"❌ 未知のツール: {tool_name}"
        except Exception as e:
            return f"❌ {tool_name} エラー: {e}"
