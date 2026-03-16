# LINE Agent セットアップ手順

LINEを受け口にして、Macのファイル操作・コマンド実行・Google Driveを自然言語で操作するシステム。

---

## ステップ1: LINE Bot の作成

1. [LINE Developers Console](https://developers.line.biz/) にアクセス
2. 「新規プロバイダー作成」→ 名前を入力（例: My Agent）
3. 「新規チャンネル作成」→「Messaging API」を選択
4. チャンネル名・説明・業種を入力して作成
5. チャンネルページで以下を取得:
   - **チャンネルシークレット**: 「Basic settings」タブ → Channel secret
   - **チャンネルアクセストークン**: 「Messaging API」タブ → 「Issue」ボタンで発行

---

## ステップ2: ngrok のインストール

```bash
brew install ngrok
```

または [ngrok.com](https://ngrok.com) でアカウント作成後:
```bash
ngrok config add-authtoken <your_token>
```

---

## ステップ3: 自分のLINE User IDを取得

```bash
cd ~/line-agent

# .envを作成（Channel SecretとTokenだけ先に設定）
cp .env.example .env
# → LINE_CHANNEL_ACCESS_TOKEN と LINE_CHANNEL_SECRET を .env に記入

# 別ターミナルでngrok起動
ngrok http 8080

# User ID取得サーバー起動
python get_line_user_id.py
```

LINE Developers Console で Webhook URL を以下に設定:
```
https://xxxx.ngrok-free.app/webhook_debug
```

→ 自分のBotにLINEでメッセージを送ると、ターミナルに User ID が表示される

---

## ステップ4: .env を完成させる

```bash
nano .env
```

```env
LINE_CHANNEL_ACCESS_TOKEN=（ステップ1で取得）
LINE_CHANNEL_SECRET=（ステップ1で取得）
LINE_AUTHORIZED_USER_ID=（ステップ3で取得）
ANTHROPIC_API_KEY=（https://console.anthropic.com/ で取得）
```

---

## ステップ5: Google Drive 認証

### Google Cloud Console での設定:
1. [console.cloud.google.com](https://console.cloud.google.com/) でプロジェクト作成
2. 「APIとサービス」→「ライブラリ」→「Google Drive API」を有効化
3. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
4. アプリの種類: **デスクトップアプリ**
5. 「JSONをダウンロード」→ `credentials.json` にリネームして `~/line-agent/` に配置

### 認証実行:
```bash
cd ~/line-agent
python auth_drive.py
```
→ ブラウザが開くのでGoogleアカウントでログイン・許可
→ `token.json` が生成されれば完了

---

## ステップ6: サーバー起動

```bash
cd ~/line-agent
bash start.sh
```

表示された ngrok URL を LINE Developers Console の Webhook URL に設定:
```
https://xxxx.ngrok-free.app/webhook
```

「Verify」ボタンで検証 → 成功したら完了！

---

## 使い方（LINEで話しかけるだけ）

```
「myapp というフォルダを作って」
→ /Users/sekimotokaito/myapp/ が作成される

「myapp/README.md を作って。内容は「# My App\n概要をここに書く」」
→ ファイルが作成される

「myapp フォルダをGoogleDriveにアップして」
→ Drive にアップロードされ、URLが返ってくる

「myapp で git init して、npm init -y もやって」
→ コマンドが実行される

「Driveのルートのファイル一覧を見せて」
→ Drive のファイル・フォルダ一覧が返ってくる
```

---

## ファイル構成

```
~/line-agent/
├── main.py              # FastAPI サーバー（LINE Webhook受信）
├── agent.py             # Claude Sonnet エージェント（ツール付き）
├── actions/
│   ├── computer.py      # ローカルファイル操作・コマンド実行
│   └── google_drive.py  # Google Drive 操作
├── auth_drive.py        # Google Drive 初回認証
├── get_line_user_id.py  # LINE User ID 取得ツール
├── start.sh             # 起動スクリプト
├── requirements.txt
├── .env                 # 設定（gitignoreに含めること）
├── credentials.json     # Google OAuth認証情報（gitignoreに含めること）
└── token.json           # Google認証トークン（自動生成）
```
