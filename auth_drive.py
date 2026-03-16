#!/usr/bin/env python3
"""
Google Drive OAuth2 認証の初回セットアップスクリプト
実行: python auth_drive.py
"""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def main():
    if not CREDENTIALS_FILE.exists():
        print("❌ credentials.json が見つかりません")
        print()
        print("【取得手順】")
        print("1. https://console.cloud.google.com/ にアクセス")
        print("2. プロジェクトを作成（または既存を選択）")
        print("3. 「APIとサービス」→「ライブラリ」→「Google Drive API」を有効化")
        print("4. 「APIとサービス」→「認証情報」→「認証情報を作成」")
        print("5. 「OAuthクライアントID」→「デスクトップアプリ」を選択")
        print("6. 「JSONをダウンロード」→ credentials.json にリネームしてこのフォルダに配置")
        print(f"\n配置先: {CREDENTIALS_FILE}")
        return

    print("🔐 Google Drive の認証を開始します...")
    print("ブラウザが自動的に開きます。Googleアカウントでログインして許可してください。")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\n✅ 認証成功！token.json を保存しました")
    print(f"保存先: {TOKEN_FILE}")
    print("\nこれでサーバーからGoogle Drive・Calendar・Sheetsにアクセスできます。")


if __name__ == "__main__":
    main()
