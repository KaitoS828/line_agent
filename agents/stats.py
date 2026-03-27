"""統計担当エージェント — 利用統計の取得・レポート"""

from actions.activity_log import get_today_stats, get_weekly_stats


class StatsAgent:
    """利用統計のレポートを提供するエージェント"""

    def __init__(self):
        self.name = "StatsAgent"
        self.role = "利用統計・アクティビティレポートの専門家。「統計見せて」「今日何回使った？」「週間レポート」に対応"

    def run(self, task: str) -> str:
        task_lower = task.lower()
        if "週" in task or "week" in task_lower or "7日" in task:
            return get_weekly_stats()

        # Default: both today + weekly
        today = get_today_stats()
        weekly = get_weekly_stats()
        return f"{today}\n\n{weekly}"
