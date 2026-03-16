import os
import subprocess
from pathlib import Path


class ComputerActions:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_dir / p

    def create_folder(self, path: str) -> str:
        full_path = self._resolve_path(path)
        full_path.mkdir(parents=True, exist_ok=True)
        return f"✅ フォルダ作成: {full_path}"

    def create_file(self, path: str, content: str) -> str:
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"✅ ファイル作成: {full_path} ({len(content)} chars)"

    def read_file(self, path: str) -> str:
        full_path = self._resolve_path(path)
        if not full_path.exists():
            return f"❌ ファイルが見つかりません: {full_path}"
        content = full_path.read_text(encoding="utf-8")
        if len(content) > 8000:
            return content[:8000] + "\n...(省略)"
        return content

    def edit_file(self, path: str, content: str, mode: str = "overwrite") -> str:
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"✅ 追記完了: {full_path}"
        else:
            full_path.write_text(content, encoding="utf-8")
            return f"✅ 上書き完了: {full_path}"

    def list_directory(self, path: str) -> str:
        full_path = self._resolve_path(path)
        if not full_path.exists():
            return f"❌ ディレクトリが見つかりません: {full_path}"
        items = []
        for item in sorted(full_path.iterdir()):
            icon = "📁" if item.is_dir() else "📄"
            items.append(f"{icon} {item.name}")
        if not items:
            return f"{full_path}: (空のディレクトリ)"
        return f"📂 {full_path}:\n" + "\n".join(items)

    def run_command(self, command: str, cwd: str = None) -> str:
        working_dir = Path(cwd) if cwd else self.base_dir
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n(exit code: {result.returncode})"
            return output[:5000] if output else "(出力なし)"
        except subprocess.TimeoutExpired:
            return "❌ タイムアウト（120秒）"
        except Exception as e:
            return f"❌ コマンド実行エラー: {str(e)}"
