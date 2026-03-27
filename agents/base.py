"""全エージェント共通の基底クラス"""

import anthropic
from config import ANTHROPIC_API_KEY


class BaseAgent:
    """専門エージェントの基底クラス。Claudeのツール使用ループを実装。"""

    def __init__(self, name: str, role: str, system_prompt: str, tools: list):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.name = name
        self.role = role  # 1行の役職説明（CEOが参照）
        self.system_prompt = system_prompt
        self.tools = tools

    def run(self, task: str) -> str:
        """タスクを受け取り、ツールを使いながら結果を返す"""
        messages = [{"role": "user", "content": task}]

        for _ in range(10):
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return "✅ 完了しました。"

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return "✅ 処理が完了しました。"

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        raise NotImplementedError(f"{self.name} は {tool_name} を実装していません")
