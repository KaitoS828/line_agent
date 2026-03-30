"""Twitter/X読み取りアクション — bird CLI経由（APIキー不要・cookie認証）"""

import re
import shutil
import subprocess


def _bird_available() -> bool:
    return bool(shutil.which("bird") or shutil.which("birdx"))


def _run_bird(args: list[str], timeout: int = 30) -> tuple[bool, str]:
    """bird CLIを実行して (success, output) を返す"""
    binary = shutil.which("bird") or shutil.which("birdx")
    if not binary:
        return False, "❌ bird CLI がインストールされていません（npm install -g @steipete/bird）"
    try:
        result = subprocess.run(
            [binary] + args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = result.stdout or result.stderr or ""
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "❌ bird CLI がタイムアウトしました"
    except Exception as e:
        return False, f"❌ bird CLI エラー: {e}"


def get_tweet(url: str, max_chars: int = 2000) -> str:
    """ツイートのURLから内容を取得"""
    if not _bird_available():
        # Jina Reader fallback
        from actions.url_extract import fetch_page_content
        return fetch_page_content(url, max_chars)

    ok, output = _run_bird(["get", url])
    if not ok:
        return output
    return output[:max_chars]


def search_tweets(query: str, max_results: int = 10) -> str:
    """Twitter/Xでツイートを検索"""
    if not _bird_available():
        return "❌ bird CLI がインストールされていません（npm install -g @steipete/bird）\nTwitter検索を使うには `npm install -g @steipete/bird` を実行してください"

    ok, output = _run_bird(["search", query, "--count", str(max_results)])
    if not ok:
        return output
    return output[:3000]


def get_user_timeline(username: str, max_results: int = 10) -> str:
    """ユーザーのタイムラインを取得（@なしで指定）"""
    if not _bird_available():
        return "❌ bird CLI がインストールされていません"

    ok, output = _run_bird(["user", username, "--count", str(max_results)])
    if not ok:
        return output
    return output[:3000]


def is_twitter_url(url: str) -> bool:
    return bool(re.search(r"(x\.com|twitter\.com)", url))
