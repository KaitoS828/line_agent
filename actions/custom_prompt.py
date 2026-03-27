"""カスタムプロンプト管理 — ユーザーがLINEからキャラ設定を微調整"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CUSTOM_FILE = DATA_DIR / "custom_prompt.json"


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CUSTOM_FILE.exists():
        CUSTOM_FILE.write_text("{}", encoding="utf-8")


def _load() -> dict:
    _ensure()
    return json.loads(CUSTOM_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    _ensure()
    CUSTOM_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_custom_instruction(user_id: str, instruction: str) -> str:
    """ユーザーのカスタム指示を保存"""
    data = _load()
    if user_id not in data:
        data[user_id] = {"instructions": []}

    data[user_id]["instructions"].append(instruction)
    # Max 10 instructions
    data[user_id]["instructions"] = data[user_id]["instructions"][-10:]
    _save(data)
    return f"✅ カスタム指示を保存: 「{instruction}」"


def get_custom_instructions(user_id: str) -> str:
    """ユーザーのカスタム指示を取得（システムプロンプト追記用）"""
    data = _load()
    user_data = data.get(user_id, {})
    instructions = user_data.get("instructions", [])
    if not instructions:
        return ""
    return "\n## ユーザーからの追加指示\n" + "\n".join(f"- {i}" for i in instructions)


def list_custom_instructions(user_id: str) -> str:
    """カスタム指示の一覧を返す"""
    data = _load()
    user_data = data.get(user_id, {})
    instructions = user_data.get("instructions", [])
    if not instructions:
        return "カスタム指示はまだ設定されていません"
    lines = ["📋 現在のカスタム指示:"]
    for i, inst in enumerate(instructions, 1):
        lines.append(f"  {i}. {inst}")
    return "\n".join(lines)


def clear_custom_instructions(user_id: str) -> str:
    """カスタム指示を全てクリア"""
    data = _load()
    if user_id in data:
        data[user_id]["instructions"] = []
        _save(data)
    return "✅ カスタム指示をすべてクリアしました"


def remove_custom_instruction(user_id: str, index: int) -> str:
    """指定番号のカスタム指示を削除"""
    data = _load()
    user_data = data.get(user_id, {})
    instructions = user_data.get("instructions", [])
    if index < 1 or index > len(instructions):
        return f"❌ 指示番号 {index} は存在しません（1〜{len(instructions)}）"
    removed = instructions.pop(index - 1)
    data[user_id]["instructions"] = instructions
    _save(data)
    return f"✅ 削除: 「{removed}」"
