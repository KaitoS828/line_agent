"""アクティビティログ — 利用統計の記録・集計"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
LOG_DIR = Path(__file__).parent.parent / "data" / "activity_logs"


def _ensure_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _today_file() -> Path:
    return LOG_DIR / f"{datetime.now(JST).strftime('%Y-%m-%d')}.json"


def _load_log(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"date": path.stem, "total_requests": 0, "by_type": {}, "by_hour": {}}


def _save_log(path: Path, data: dict):
    _ensure_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_request(request_type: str = "text") -> None:
    """リクエストを記録"""
    path = _today_file()
    data = _load_log(path)
    data["total_requests"] += 1
    data["by_type"][request_type] = data["by_type"].get(request_type, 0) + 1
    hour = str(datetime.now(JST).hour)
    data["by_hour"][hour] = data["by_hour"].get(hour, 0) + 1
    _save_log(path, data)


def get_today_stats() -> str:
    """今日の利用統計を返す"""
    data = _load_log(_today_file())
    if data["total_requests"] == 0:
        return "📊 今日はまだリクエストがありません"

    lines = [f"📊 今日の利用統計 ({data['date']})"]
    lines.append(f"  合計: {data['total_requests']}回")

    if data["by_type"]:
        lines.append("  種別:")
        for t, count in sorted(data["by_type"].items()):
            lines.append(f"    • {t}: {count}回")

    if data["by_hour"]:
        peak_hour = max(data["by_hour"], key=lambda h: data["by_hour"][h])
        lines.append(f"  ピーク時間帯: {peak_hour}時台")

    return "\n".join(lines)


def get_weekly_stats() -> str:
    """過去7日間の利用統計を返す"""
    _ensure_dir()
    now = datetime.now(JST)
    total = 0
    daily = []

    for i in range(7):
        date = now - timedelta(days=i)
        path = LOG_DIR / f"{date.strftime('%Y-%m-%d')}.json"
        data = _load_log(path)
        count = data["total_requests"]
        total += count
        if count > 0:
            daily.append(f"  {data['date']}: {count}回")

    lines = [f"📊 週間統計（過去7日間）", f"  合計: {total}回"]
    if daily:
        lines.append("  日別:")
        lines.extend(daily)
    else:
        lines.append("  データなし")

    return "\n".join(lines)
