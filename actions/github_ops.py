"""GitHub操作アクション — git status / commit / push を安全実行"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_git(args: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return completed.returncode == 0, output.strip() or "(出力なし)"
    except Exception as e:
        return False, f"git実行エラー: {e}"


def repo_status() -> str:
    ok, out = _run_git(["status", "--short", "--branch"])
    if not ok:
        return f"❌ status取得失敗\n{out}"
    return f"📌 現在の状態\n{out}"


def commit_changes(message: str, include_untracked: bool = True) -> str:
    commit_message = message.strip()
    if not commit_message:
        return "❌ コミットメッセージが空です"

    add_args = ["add", "-A"] if include_untracked else ["add", "-u"]
    ok, out = _run_git(add_args)
    if not ok:
        return f"❌ 変更のステージングに失敗\n{out}"

    ok, status = _run_git(["status", "--short"])
    if not ok:
        return f"❌ ステージ後の状態確認に失敗\n{status}"
    if not status.strip():
        return "ℹ️ コミット対象の変更がありません"

    ok, out = _run_git(["commit", "-m", commit_message])
    if not ok:
        return f"❌ コミット失敗\n{out}"
    return f"✅ コミット完了\n{out}"


def push_current_branch() -> str:
    ok, out = _run_git(["push"])
    if not ok:
        # upstream未設定時は自動で -u origin HEAD を試す
        ok2, out2 = _run_git(["push", "-u", "origin", "HEAD"])
        if not ok2:
            return f"❌ push失敗\n{out}\n\n再試行結果:\n{out2}"
        return f"✅ push完了（upstream設定）\n{out2}"
    return f"✅ push完了\n{out}"


def commit_and_push(message: str, include_untracked: bool = True) -> str:
    commit_result = commit_changes(message=message, include_untracked=include_untracked)
    if commit_result.startswith("❌"):
        return commit_result
    if "コミット対象の変更がありません" in commit_result:
        return f"{commit_result}\n\n必要なら push は個別に実行してください"
    push_result = push_current_branch()
    return f"{commit_result}\n\n{push_result}"
