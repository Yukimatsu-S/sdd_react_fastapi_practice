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