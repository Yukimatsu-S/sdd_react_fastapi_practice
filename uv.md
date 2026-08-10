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