# セットアップ手順書

## 1. uv を Mac に入れる
以下のコマンドで実行

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

以下のような表示が出たらインストール成功

```txt
downloading uv 0.12.3 aarch64-apple-darwin
installing to /Users/yukimatsusugawara/.local/bin
  uv
  uvx
everything's installed!

To add $HOME/.local/bin to your PATH, either restart your shell or run:

    source $HOME/.local/bin/env (sh, bash, zsh)
    source $HOME/.local/bin/env.fish (fish)
```

PATH を追加するために shell をリスタートするか、以下のコマンドを実行すると書いてあるので従う

以下のコマンドで uv のバージョンが確認できたら正常にインストールできている

```shell
uv --version
```

## 2. Python のインストール

今回はグローバルの Python を使わず、 uv 管理の Python を使うため、 uv 経由で Python をインストールする  
これはどの階層から行ってもよい、グローバルレベルの uv が管理するため

```shell
uv python install 3.12
```

以下のコマンドで、今いるプロジェクトで実際にどの Python が使われるかを確認できる

```shell
uv run python --version
```

今いるプロジェクトにどの Python が使われるか指定したい場合は以下のコマンドを実行する

```shell
uv python pin 3.12
```

# 3. spec-kit の導入

現在のGitHubリリースはv0.16.1で、公式リリースページでは以下のインストールコマンドが案内されている

```shell
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v0.16.1
```

以下のコマンドでバージョンの確認ができたら正常にインストールできている

```shell
specify version
```

期待出力は以下

```shell
specify version                     
                                                  ███████╗██████╗ ███████╗ ██████╗██╗███████╗██╗   ██╗                                                   
                                                  ██╔════╝██╔══██╗██╔════╝██╔════╝██║██╔════╝╚██╗ ██╔╝                                                   
                                                  ███████╗██████╔╝█████╗  ██║     ██║█████╗   ╚████╔╝                                                    
                                                  ╚════██║██╔═══╝ ██╔══╝  ██║     ██║██╔══╝    ╚██╔╝                                                     
                                                  ███████║██║     ███████╗╚██████╗██║██║        ██║                                                      
                                                  ╚══════╝╚═╝     ╚══════╝ ╚═════╝╚═╝╚═╝        ╚═╝                                                      
                                                                                                                                                         
                                                    GitHub Spec Kit - Spec-Driven Development Toolkit                                                    

╭─────────────────────────────────────────────────────────────── Specify CLI Information ───────────────────────────────────────────────────────────────╮
│                                                                                                                                                       │
│     CLI Version    0.16.1                                                                                                                             │
│                                                                                                                                                       │
│          Python    3.12.13                                                                                                                            │
│        Platform    Darwin                                                                                                                             │
│    Architecture    arm64                                                                                                                              │
│      OS Version    Darwin Kernel Version 25.5.0: Mon Apr 27 20:40:51 PDT 2026; root:xnu-12377.121.6~2/RELEASE_ARM64_T8112                             │
│                                                                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

以下のコマンドで Spec Kitを使うための周辺ツールがPCに入っているか確認する  
具体的には、CLI型のAIコーディングエージェントや VS Code などが利用可能かをチェックする

```shell
specify check
```

プロジェクトのルートディレクトリに移動して以下のコマンドを実行することで  
Spec Kit対応プロジェクトとして初期化する

```shell
specify init --here --integration copilot
```

または

```shell
specify init . --integration copilot
```

<details>

**注意点**  
GitHub Spec Kit と Git は別ものなので、初期化する際にすでにディレクトリにファイルがある場合は `git init` してから  
Spec Kit を初期化すると安全

```shell
git init
git add .
git commit -m "docs: add initial learning notes"
```

**他の初期化方法**  
新たにディレクトリを作成して、そこを Spec Kit 対応プロジェクトとして初期化する場合は以下のように指定して初期化する

```shell
specify init my-project --integration copilot
cd my-project
```

</details>

choose script type は `sh` を選択する

セットアップが完了すると以下のようなものが出力される

```shell       
                                                  ███████╗██████╗ ███████╗ ██████╗██╗███████╗██╗   ██╗                                                   
                                                  ██╔════╝██╔══██╗██╔════╝██╔════╝██║██╔════╝╚██╗ ██╔╝                                                   
                                                  ███████╗██████╔╝█████╗  ██║     ██║█████╗   ╚████╔╝                                                    
                                                  ╚════██║██╔═══╝ ██╔══╝  ██║     ██║██╔══╝    ╚██╔╝                                                     
                                                  ███████║██║     ███████╗╚██████╗██║██║        ██║                                                      
                                                  ╚══════╝╚═╝     ╚══════╝ ╚═════╝╚═╝╚═╝        ╚═╝                                                      
                                                                                                                                                         
                                                    GitHub Spec Kit - Spec-Driven Development Toolkit                                                    

Warning: Current directory is not empty (5 items)
Template files will be merged with existing content and may overwrite existing files. Do you want to continue? [y/N]: y
╭───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                       │
│  Specify Project Setup                                                                                                                                │
│                                                                                                                                                       │
│  Project         sdd_react_fastapi_practice                                                                                                           │
│  Working Path    /Users/yukimatsusugawara/project_rich/sdd_react_fastapi_practice                                                                     │
│                                                                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Selected coding agent integration: copilot
Selected script type: sh
Initialize Specify Project
├── ● Check required tools (ok)
├── ● Select coding agent integration (copilot)
├── ● Select script type (sh)
├── ● Install integration (GitHub Copilot)
├── ● Install shared infrastructure (scripts (sh) + templates)
├── ● Ensure scripts executable (5 updated)
├── ● Constitution setup (copied from template)
├── ● Install bundled workflow (speckit installed)
└── ● Finalize (project ready)

Project ready.

╭──────────────────────────────────────────────────────────────── Agent Folder Security ────────────────────────────────────────────────────────────────╮
│                                                                                                                                                       │
│  Some agents may store credentials, auth tokens, or other identifying and private artifacts in the agent folder within your project.                  │
│  Consider adding .github/ (or parts of it) to .gitignore to prevent accidental credential leakage.                                                    │
│                                                                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────────────────────────────────────────────── Next Steps ──────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                       │
│  1. You're already in the project directory!                                                                                                          │
│  2. Start using skills with your coding agent:                                                                                                        │
│     2.1 /speckit-constitution - Establish project principles                                                                                          │
│     2.2 /speckit-specify - Create baseline specification                                                                                              │
│     2.3 /speckit-plan - Create implementation plan                                                                                                    │
│     2.4 /speckit-tasks - Generate actionable tasks                                                                                                    │
│     2.5 /speckit-implement - Execute implementation                                                                                                   │
│     2.6 /speckit-converge - Assess the codebase and append remaining work as tasks                                                                    │
│                                                                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────────────────────────────────────────── Enhancement Skills ──────────────────────────────────────────────────────────────────╮
│                                                                                                                                                       │
│  Optional skills that you can use for your specs (improve quality & confidence)                                                                       │
│                                                                                                                                                       │
│  ○ /speckit-clarify (optional) - Ask structured questions to de-risk ambiguous areas before planning (run before /speckit-plan if used)               │
│  ○ /speckit-analyze (optional) - Cross-artifact consistency & alignment report (after /speckit-tasks, before /speckit-implement)                      │
│  ○ /speckit-checklist (optional) - Generate quality checklists to validate requirements completeness, clarity, and consistency (after /speckit-plan)  │
│                                                                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```