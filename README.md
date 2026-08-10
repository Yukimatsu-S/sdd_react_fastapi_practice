# 今回のプロジェクトで使用するもののイメージ

```txt
Mac本体
│
├─ Git                  ← OS側のツール
├─ Node.js / npm        ← JavaScript実行環境・パッケージ管理
├─ uv                   ← Python環境・パッケージ管理ツール
│   ├─ specify-cli      ← uv toolで独立してインストール
│   │   └─ specify コマンド
│   │
│   └─ backend/.venv    ← 後でFastAPI用に作るPython環境
│       └─ FastAPI
│
└─ プロジェクト
    ├─ frontend/         ← React
    └─ backend/          ← FastAPI
```

**それぞれの依存関係の管理方法**

```txt
React → npm

FastAPI → uv

spec-kit CLI → uv tool

Git → OSレベル
```

**実際にインストールするものたちの概要**

| ツール         | 置き場所          | 用途           |
| ----------- | ------------- | ------------ |
| Git         | Mac側          | Git管理        |
| Node.js     | Mac側          | React/Vite実行 |
| npm         | Node.jsと一緒    | React依存管理    |
| uv          | ユーザー環境        | Python環境管理   |
| Python      | uvに管理させてもOK   | FastAPI実行    |
| specify-cli | `uv tool`     | Spec Kit CLI |
| FastAPI     | プロジェクト`.venv` | Backend      |


# キーワード概要

## GitHub spec-kit

## React

## FastAPI



# メモ

- spec-kitというプロジェクトが提供しているCLIパッケージの名前がspecify-cli
- ReactとFastAPIで、依存関係の管理方法がそもそも違う
- uvはプロジェクトごとに.venvを作り、依存パッケージをそこへ隔離して管理できる、つまりわざわざ venv を作成しなくて済む
