# uv はレイヤー別に管理することができる

イメージ図

```txt
Mac
│
├─ Node.js
│   └─ npm
│
├─ Git
│
└─ uv
    │
    ├─ Python管理
    │   └─ Python 3.12
    │
    ├─ Tool管理
    │   └─ specify-cli
    │       └─ specify コマンド
    │
    └─ Project管理
        └─ sdd-react-fastapi-practice/
            │
            ├─ frontend/
            │   └─ node_modules/
            │
            └─ backend/
                └─ .venv/
                    └─ FastAPI
```

このような階層に位置し、 Python本体・CLIツール・プロジェクト依存関係の3階層をuvがそれぞれ別に管理している

#　インストール方法の違い

## `uv tool install <cli>`

cli専用の隔離された環境へインストールして、その実行コマンドをPATHから使えるようにする  
つまり、インストールした cli をどのプロジェクトからでも使えるようにする

## `uv add `

プロジェクトの依存関係をインストールするためのコマンド  
プロジェウト単位の環境で管理される  
.venv に近い

# プロジェクト依存関係の管理方法

プロジェクトルートで以下のコマンドを実行することでそのディレクトリをuvで管理するPythonプロジェクトとして初期化する

```shell
uv init
```

このコマンドは、普通のPythonアプリケーションとして初期化する  
以下のように、すぐPythonコードを書き始められる雛形まで作ってくれる

```txt
my-project/
├── .python-version
├── README.md
├── main.py
└── pyproject.toml
```

以下のコマンドでは、uvで依存関係を管理するための土台だけ用意する、つまり bare（必要最低限）の初期化のみ行う

```shell
uv init --bare
```

