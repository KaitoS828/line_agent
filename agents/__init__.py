"""エージェント社員名簿 — 全専門エージェントの登録・初期化"""

from agents.coder import CoderAgent
from agents.researcher import ResearcherAgent
from agents.transcriber import TranscriberAgent
from agents.vision import VisionAgent
from agents.calendar_mgr import CalendarMgrAgent
from agents.drive_mgr import DriveMgrAgent
from agents.sheets_mgr import SheetsMgrAgent
from agents.web_searcher import WebSearcherAgent
from agents.gmail_mgr import GmailMgrAgent
from agents.task_mgr import TaskMgrAgent
from agents.monitor_mgr import MonitorMgrAgent


def create_all_agents(google_creds=None) -> dict:
    """全エージェントを初期化して辞書で返す"""
    return {
        "coder": CoderAgent(),
        "researcher": ResearcherAgent(),
        "transcriber": TranscriberAgent(),
        "vision": VisionAgent(),
        "calendar": CalendarMgrAgent(google_creds),
        "drive": DriveMgrAgent(google_creds),
        "sheets": SheetsMgrAgent(google_creds),
        "web_search": WebSearcherAgent(),
        "gmail": GmailMgrAgent(google_creds),
        "task": TaskMgrAgent(),
        "monitor": MonitorMgrAgent(),
    }


# CEOが参照する社員一覧（名前 → 役職説明）
def get_agent_directory(agents: dict) -> str:
    """CEOのシステムプロンプトに埋め込む社員名簿を生成"""
    lines = []
    for key, agent in agents.items():
        lines.append(f"- {key}: {agent.role}")
    return "\n".join(lines)
