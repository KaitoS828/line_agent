# LINE Agent 🤖

LINEを受け口にして、MacのPC操作・Google Driveを自然言語で操作するAIエージェント。

Claude Sonnet 4.6 が搭載されており、LINEでメッセージを送るだけでファイル操作・コマンド実行・Google Drive連携が可能。

---

## 機能

| カテゴリ | できること |
|---|---|
| 📁 ローカルファイル | 作成・読み取り・編集・一覧表示 |
| 💻 コマンド実行 | `git`, `npm`, `python`, `brew` など |
| ☁️ Google Drive | フォルダ作成・ファイルアップロード・読み書き・一覧表示 |

---

## アーキテクチャ

```
LINEアプリ
    ↓ メッセージ送信
LINE Webhook (FastAPI)
    ↓
Claude Sonnet 4.6（ツール付き）
    ↓ ツール選択・実行
ローカルPC操作 / Google Drive API
    ↓ 結果
LINEにプッシュ通知
```

---

## セットアップ

### 必要なもの

- Python 3.11+
- [LINE Bot チャンネル](https://developers.line.biz/)
- [Anthropic API キー](https://console.anthropic.com/)
- [Google Cloud プロジェクト](https://console.cloud.google.com/)（Drive API有効化）
- ngrok（ローカル起動時のみ）

### インストール

```bash
git clone https://github.com/KaitoS828/line_agent.git
cd line_agent
pip install -r requirements.txt
```

### 環境変数の設定

```bash
cp .env.example .env
```

`.env` に以下を記入：

```env
LINE_CHANNEL_ACCESS_TOKEN=（LINE Developers > Messaging API > Channel access token）
LINE_CHANNEL_SECRET=（LINE Developers > Basic settings > Channel secret）
LINE_AUTHORIZED_USER_ID=（python get_line_user_id.py で取得）
ANTHROPIC_API_KEY=（https://console.anthropic.com/）
GOOGLE_TOKEN_JSON=（token.json の中身をJSON文字列で）
```

### Google Drive 認証（初回のみ）

1. Google Cloud Console で Drive API を有効化
2. OAuth クライアントID（デスクトップ）を作成
3. `credentials.json` をダウンロードしてプロジェクトルートに配置
4. 認証を実行：

```bash
python auth_drive.py
```

→ `token.json` が生成されます。中身を `GOOGLE_TOKEN_JSON` 環境変数に設定してください。

### LINE User ID の取得

```bash
# ターミナル1
python get_line_user_id.py

# ターミナル2
ngrok http 8080
```

LINE Developers の Webhook URL を `https://xxxx.ngrok-free.app/webhook_debug` に設定し、BotにLINEでメッセージを送ると User ID が表示されます。

---

## 起動方法

### ローカル

```bash
bash start.sh
```

ngrok URL を LINE Developers の Webhook URL に設定：
```
https://xxxx.ngrok-free.app/webhook
```

### Railway（本番）

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

1. Railway で GitHub リポジトリを連携
2. 環境変数を Variables タブで設定
3. 自動デプロイ完了後、発行されたドメインを LINE の Webhook URL に設定

---

## 使用例

```
「デスクトップにmemo.txtを作って。内容は「今日のTODO」」
→ /Users/xxx/Desktop/memo.txt が作成される

「~/projectsフォルダの一覧を見せて」
→ フォルダ内容が返ってくる

「face-portfolioでgit statusして」
→ コマンド結果が返ってくる

「DriveのルートにTODO.txtを作って。内容は「タスク1」」
→ Google Driveにファイルが作成されURLが返ってくる
```

---

## ファイル構成

```
line-agent/
├── main.py              # FastAPI サーバー（LINE Webhook受信）
├── agent.py             # Claude Sonnet エージェント（ツールループ）
├── actions/
│   ├── computer.py      # ローカルPC操作（ファイル/コマンド）
│   └── google_drive.py  # Google Drive 操作
├── auth_drive.py        # Google Drive 初回認証ツール
├── get_line_user_id.py  # LINE User ID 取得ツール
├── start.sh             # ローカル起動スクリプト
├── Procfile             # Railway/Heroku 用
├── railway.toml         # Railway 設定
└── requirements.txt
```

---

## 技術スタック

- **FastAPI** - Webhook サーバー
- **Claude Sonnet 4.6** - AI エージェント（Anthropic SDK）
- **LINE Messaging API** - メッセージング
- **Google Drive API** - クラウドストレージ連携
- **Railway** - クラウドホスティング
