"""モード別プロンプト担当エージェント — 場面に応じた文章生成"""

import anthropic
from pathlib import Path
from config import ANTHROPIC_API_KEY

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(mode: str) -> str:
    """プロンプトファイルを読み込む"""
    path = PROMPTS_DIR / f"{mode}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def list_modes() -> str:
    """利用可能なモード一覧を返す"""
    modes = [p.stem for p in PROMPTS_DIR.glob("*.txt")]
    if not modes:
        return "利用可能なモードはありません"
    lines = ["📝 利用可能なモード:"]
    for m in sorted(modes):
        lines.append(f"  • {m}")
    return "\n".join(lines)


class PromptModeAgent:
    """場面別プロンプトで文章を生成するエージェント"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.name = "PromptModeAgent"
        self.role = "モード別文章生成（要約・X投稿・メモ・翻訳など）の専門家。「要約して」「Xの投稿にして」「メモにまとめて」「翻訳して」のような依頼に対応"

    def run(self, task: str) -> str:
        """タスク文字列からモードを判定して生成"""
        # CEOからは "mode:summary\n本文..." の形式で来る想定
        mode = "summary"  # default
        content = task

        if "\n" in task:
            first_line = task.split("\n", 1)[0].strip()
            if first_line.startswith("mode:"):
                mode = first_line.replace("mode:", "").strip()
                content = task.split("\n", 1)[1].strip()

        prompt_text = _load_prompt(mode)
        if not prompt_text:
            return f"❌ モード「{mode}」のプロンプトが見つかりません。\n{list_modes()}"

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=prompt_text,
            messages=[{"role": "user", "content": content}],
        )

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "生成に失敗しました。"
