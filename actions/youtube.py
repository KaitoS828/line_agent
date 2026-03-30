"""YouTube字幕・情報取得アクション — yt-dlp経由（APIキー不要）"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs


def _is_youtube_url(url: str) -> bool:
    d = urlparse(url).netloc.lower()
    return "youtube.com" in d or "youtu.be" in d


def get_transcript(url: str, max_chars: int = 5000) -> str:
    """YouTube動画の字幕（日本語優先、なければ英語）を取得"""
    if not shutil.which("yt-dlp"):
        return "❌ yt-dlp がインストールされていません（pip install yt-dlp）"

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-langs", "ja,en",
            "--skip-download",
            "--output", f"{tmpdir}/%(id)s",
            "--no-playlist",
            url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            return "❌ 字幕取得がタイムアウトしました"
        except Exception as e:
            return f"❌ yt-dlp エラー: {e}"

        # .vtt または .srt ファイルを探す
        sub_files = list(Path(tmpdir).glob("*.vtt")) + list(Path(tmpdir).glob("*.srt"))
        if not sub_files:
            return "字幕が見つかりませんでした（字幕なし動画の可能性があります）"

        # 日本語優先
        ja_files = [f for f in sub_files if ".ja." in f.name]
        target = ja_files[0] if ja_files else sub_files[0]

        raw = target.read_text(encoding="utf-8", errors="replace")
        text = _clean_subtitles(raw)
        return text[:max_chars] if text else "字幕テキストを取得できませんでした"


def get_video_info(url: str) -> str:
    """YouTube動画のメタ情報（タイトル・説明・再生数など）を取得"""
    if not shutil.which("yt-dlp"):
        return "❌ yt-dlp がインストールされていません"

    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, encoding="utf-8", timeout=30)
        if result.returncode != 0:
            return f"❌ 動画情報取得エラー: {result.stderr[:200]}"
        data = json.loads(result.stdout)
        lines = [
            f"タイトル: {data.get('title', '不明')}",
            f"チャンネル: {data.get('uploader', '不明')}",
            f"再生時間: {_format_duration(data.get('duration', 0))}",
            f"再生数: {data.get('view_count', '不明'):,}" if isinstance(data.get('view_count'), int) else f"再生数: {data.get('view_count', '不明')}",
            f"投稿日: {data.get('upload_date', '不明')}",
        ]
        desc = data.get("description", "")
        if desc:
            lines.append(f"説明: {desc[:300]}...")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 動画情報取得エラー: {e}"


def _clean_subtitles(raw: str) -> str:
    """VTT/SRT形式の字幕ファイルからプレーンテキストを抽出"""
    # VTTヘッダー除去
    raw = re.sub(r'^WEBVTT.*?\n\n', '', raw, flags=re.DOTALL)
    # タイムスタンプ行除去
    raw = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}[^\n]*\n', '', raw)
    raw = re.sub(r'^\d+\n', '', raw, flags=re.MULTILINE)
    # VTTタグ除去
    raw = re.sub(r'<[^>]+>', '', raw)
    # 重複行の除去
    lines = []
    prev = ""
    for line in raw.splitlines():
        line = line.strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    return " ".join(lines)


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "不明"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
