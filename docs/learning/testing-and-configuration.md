# 学習ノート：設定値の検証・DB接続確認・monkeypatch

記録日：2026-09-08（T007完了後に作成、T008のRed確認まで追記）

## 目的と全体像

環境を再現する操作手順は[README](../../README.md)、開発内容は[Tasks](../../specs/001-experiment-evolution/tasks.md)を参照する。このノートは、処理の意味とデータの流れを読み直すための資料であり、仕様を新しく決める文書ではない。

理解する順番は「設定の置き場所 → 文字列の読み取り・検査 → 実際の接続 → テストの入力準備」。住所を読むことと、その住所へ実際に行くことは別である。

| 確認すること | MySQLへの通信 | 対応箇所 |
| --- | --- | --- |
| サンプルに通常用・テスト用の異なるURLが書かれているか | 不要 | `backend/tests/unit/test_test_environment.py` |
| テスト用の設定を要求すると、正しいURLを選択・検証するか | 不要 | T008でテスト作成・Red確認済み、T009の処理は未実装 |
| 指定されたDBへ実際に接続できるか | 必要 | `backend/scripts/check_test_database.py` |

> 検証とは、期待する条件を満たすか確かめること。成功しても、検証対象に含まれないことまで保証されるわけではない。

## 1. 環境変数とファイルは別

環境変数は、実行中のプログラムへ外から渡す名前付きの設定値。例えば名前が`MONDEL_TEST_DATABASE_URL`、値がDB接続先の文字列になる。

[`.env.example`](../../backend/.env.example)は記入例を載せたテキストファイル。置くだけでは環境変数にならない。`.env`という名前でも、プログラムやツールが読み込む仕組みが必要になる。

現在のサンプル確認テストは、環境変数ではなく`.env.example`を直接読む。実際の設定読み込み処理と混同しない。

## 2. 実装済み：ファイルからURLを読み取る

対象：[test_test_environment.py](../../backend/tests/unit/test_test_environment.py)

pytestが`test_test_database_url_is_separate_from_application_database()`を実行すると、その中から`read_environment_example()`が呼ばれる。

例えば、ファイルには次の行がある。

```text
MONDEL_TEST_DATABASE_URL=mysql+pymysql://mondel_test:mondel_test@127.0.0.1:3307/mondel_test
```

関数の処理を順番に追う。

1. `read_text()`：ファイル全体を文字列として読む。
2. `splitlines()`：行ごとの文字列に分ける。
3. `for line in ...`：1行ずつ取り出して`line`に入れる。
4. `line.strip()`：行の前後の空白を取り除く。
5. 空行や`#`から始まるコメント行は、`continue`で読み飛ばす。
6. `split("=", maxsplit=1)`：最初の`=`だけで名前と値に分ける。
7. `values[name] = value`：辞書に名前と値を登録する。
8. `return values`：辞書を呼び出し元のテスト関数へ返す。

手順6の直後のデータは、次のようになる。

```python
name = "MONDEL_TEST_DATABASE_URL"
value = "mysql+pymysql://mondel_test:mondel_test@127.0.0.1:3307/mondel_test"
```

手順7で、辞書にこの名前と値の組が登録される。実際の戻り値には、通常用DBとMLflowの設定も含まれる。

> 辞書（`dict`）は、名前で値を取り出せる入れ物。`maxsplit=1`は「分割は最大1回」という指定で、値に含まれる後続の`=`を壊さない。

テスト関数は、戻ってきた辞書から値を取り出す。

```python
test_database_url = make_url(environment["MONDEL_TEST_DATABASE_URL"])
```

右側から「辞書からURL文字列を取得 → `make_url()`へ渡す → 戻り値を`test_database_url`に入れる」の順で処理される。

`make_url()`はSQLAlchemyが提供する関数で、URL文字列を各部分へ分解したオブジェクトにする。DBへは接続しない。また、分解できるだけでアプリに必要な制約をすべて満たすとは限らない。[SQLAlchemy公式資料](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.engine.make_url)

```python
test_database_url.drivername  # "mysql+pymysql"
test_database_url.host        # "127.0.0.1"
test_database_url.port        # 3307
test_database_url.database    # "mondel_test"
```

`mysql+pymysql`はDBの種類と接続に使うPythonライブラリ、`host`と`port`は接続先、`database`は接続先MySQL内のDB名を表す。

最後に、例えば次の条件を確認する。

```python
assert test_database_url.database == "mondel_test"
```

- `assert`：後ろの条件が真であることを確認する。偽ならテストが失敗する。
- `.database`：オブジェクトからDB名を取り出す。
- `==`：左右が等しいか比較する。値を代入する`=`とは違う。

分かるのは、URLに書かれたDB名が期待どおりであること。DBの実在やパスワードの正しさは分からない。

## 3. 実装済み：MySQLへ実際に接続する

対象：[check_test_database.py](../../backend/scripts/check_test_database.py)

1. スクリプトを直接実行すると、末尾の`if __name__ == "__main__":`を通って`main()`が呼ばれる。
2. `main()`が`read_test_database_url()`を呼び、サンプルファイルからテスト用URLだけを取得する。
3. `make_url()`で分解し、ドライバー・ホスト・ポート・DB名が想定したローカルテスト用の値か確認する。不一致なら接続前にエラーにする。
4. `pymysql.connect(...)`へ分解した値を渡す。ここで実際にMySQLへ接続する。
5. `connection.cursor()`でSQLの実行と結果取得に使う窓口を作る。
6. `cursor.execute("SELECT 1, DATABASE(), VERSION()")`で問い合わせる。
7. `cursor.fetchone()`で結果を1行取得する。
8. 結果を期待値と比較し、一致すれば`PASS`を表示する。
9. `finally`内の`connection.close()`で、接続後にエラーが起きた場合も接続を閉じる。

手順7の期待値は、次のタプルになる。

```python
(1, "mondel_test", "8.0.46")
```

- `SELECT 1`：数値の`1`を返す。SQLを実行できたか確かめる。
- `DATABASE()`：現在選択されているDB名を返す。
- `VERSION()`：MySQLのバージョンを返す。

> SQLはDBへ問い合わせる言語。タプルは複数の値を順番付きでまとめるPythonの型。このSQLはテーブルのデータを追加・変更しない。

成功は、その時点で接続・認証・SQL実行ができ、DB名とバージョンが想定どおりだったことを示す。アプリのテーブルや保存・更新・ロールバックの正しさまでは保証しない。

## 4. 学習用の例：monkeypatchで入力をそろえる

以下は説明用のPythonコードで、実装済みのテストではない。ターミナルへ貼り付けるコマンドでもない。後から作成した実際のT008テストは第7節を参照する。

```python
import os


def test_example_environment(monkeypatch):
    monkeypatch.setenv("MONDEL_TEST_DATABASE_URL", "example-value")

    actual = os.environ["MONDEL_TEST_DATABASE_URL"]

    assert actual == "example-value"
```

ここではDBのURL検証ではなく、一時的な環境変数の設定と読み取りだけを説明している。

| 記述 | 意味 |
| --- | --- |
| `import os` | Python標準の、OSに関する機能を持つモジュールを読み込む |
| `def test_example_environment(...)` | テスト関数を定義する |
| 引数の`monkeypatch` | pytestに同名のfixtureを用意してもらう指定 |
| `monkeypatch.setenv(名前, 値)` | テスト中だけ環境変数を設定する |
| `os.environ[名前]` | 現在のPythonプロセスの環境変数から値を取得する |
| `actual` | 実際の結果を入れる変数名。Pythonの特別な単語ではない |

> fixture（フィクスチャ）は、pytestがテストの準備や後片付けを提供する仕組み。`monkeypatch`はpytest標準のfixture。プロセスは、実行中のプログラムの単位。

データの流れは次のとおり。

1. pytestが`monkeypatch`を準備してテスト関数を呼ぶ。
2. `setenv()`が、このPythonプロセスの環境変数を`"example-value"`へ変更する。
3. `os.environ[...]`から同じ文字列を取得する。
4. `assert`で期待値との一致を確認する。
5. テスト終了後、pytestが変更を元に戻す。以前の値があれば復元し、元々なければ削除する。

`.env.example`やシェルの設定ファイルは編集しない。起動済みの別のFastAPIプロセスの環境変数も変更しない。未設定のケースは`monkeypatch.delenv("MONDEL_TEST_DATABASE_URL", raising=False)`で準備できる。`raising=False`は、元から存在しなくても削除操作自体をエラーにしない指定。[pytest公式資料](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)

注意：`setenv()`一つだけでテスト全体が独立するわけではない。他の関連環境変数、`.env`読み込み、設定のキャッシュも結果に影響する場合がある。T008ではそれらも考慮して入力条件を固定する。

## 5. 理解確認で整理したこと

テスト用の設定を要求している場合、通常用DBへ勝手に切り替えてはいけない。正常な形式のURLでも、今回使用してよい接続先とは限らない。

| 状況 | 設定の選択・検証 | 実際の接続確認 |
| --- | --- | --- |
| 正常なテスト用URL、MySQLも稼働 | 成功を期待する | 接続・認証等にも問題がなければ成功 |
| 正常なテスト用URL、MySQLは停止 | 成功を期待する | 失敗 |
| テスト用URLが未設定 | エラーを期待する | 設定処理で止め、接続しない |
| テスト用URLが`こんにちは` | エラーを期待する | 設定処理で止め、接続しない |

この設定テストにHTTPステータスは登場しない。ブラウザからAPIへリクエストするテストではないため。

## 6. 実装済み部分を確認するコマンド

VS Codeでこのリポジトリを開き、新しい統合ターミナルを開く。最初に`pwd`と`ls`を入力し、`backend`と`frontend`があるリポジトリのルートにいることを確認する。ツール導入がまだなら[README](../../README.md)を先に実施する。

### サンプルファイルの確認テスト

ルートから、ターミナルへ1行ずつ入力する。

```bash
cd backend
uv run pytest tests/unit/test_test_environment.py
cd ..
```

`cd backend`は作業場所の移動、`uv run`はプロジェクトのPython環境での実行、`pytest`はテスト実行ツール、最後のパスは対象ファイル。`cd ..`でルートへ戻る。

期待結果は`1 passed`。このテストはMySQLが停止していても成功できる。

### テストDBへの接続確認

READMEの手順でテスト用MySQLを起動済みにして、ルートから入力する。

```bash
cd backend
uv run python scripts/check_test_database.py
cd ..
```

`python`はPythonコードを実行するプログラム、`scripts/check_test_database.py`は実行するファイル。pytestによるテスト実行とは異なる。

期待結果は`PASS: (1, 'mondel_test', '8.0.46')`。このノート追加時には再実行していないため、ここに記載した期待値は新たな検証結果ではない。

## 7. T008：実際のテストとRed確認

対象：[test_config.py](../../backend/tests/unit/test_config.py)、[config.py](../../backend/app/config.py)

### 入口だけを先に用意する理由

`load_settings()`が存在しないまま読み込むと、テストの準備段階で失敗する。それでは設定を検査するテスト本文へ到達できない。そこで、関数の入口と戻り値の形だけを作り、中身は`return None`のままにしている。

```python
@dataclass(frozen=True)
class Settings:
    database_url: str
    mlflow_tracking_uri: str
```

`class`は値や操作をまとめる型の定義。`database_url: str`は「この項目は文字列」という型の宣言。`@dataclass`は、これらの項目を持つ入れ物を作りやすくするPython標準の仕組み。`frozen=True`は作成後の項目への再代入を禁止する指定。ただし、この宣言だけではURLの検証や文字列型の実行時検査は行わない。

```python
def load_settings(*, testing: bool = False) -> Settings | None:
    return None
```

`*`以降は`testing=True`のように名前付きで渡す。`bool`は真偽値の型、`False`は省略時の値。`-> Settings | None`は現在の戻り値の型の宣言で、`None`は値がないことを表す。T009では実装を完成させ、正常時に必ず`Settings`を返す形にする。

`backend/app/__init__.py`は`app`をPythonパッケージとして扱う入口。`pytest.ini`の`pythonpath = .`は、この設定ファイルのある`backend`をテスト時のモジュール検索先に加える。これにより`from app.config import ...`を解決できる。

### テスト実行時のデータの流れ

1. pytestが`test_config.py`を読み込み、テストを収集する。
2. 各ケースの前に`configuration_environment()`を実行する。
3. `monkeypatch.setenv()`で通常用URL、テスト用URL、MLflow URIを既知の値にそろえる。
4. ケースごとに値を削除・変更し、`load_settings(testing=...)`を呼ぶ。
5. 現在の関数は何も読み取らず`None`を返す。
6. 期待した設定やエラーが得られないため、テストが失敗する。
7. pytestが環境変数と作業場所を元に戻す。

準備関数の`@pytest.fixture(autouse=True)`は、このファイルの各テストで明示的に引数へ書かなくても準備を実行する指定。`tmp_path`はpytestが渡す一時ディレクトリ。`monkeypatch.chdir(tmp_path)`でそこへ作業場所を移し、開発者のローカルファイルに依存しにくい条件にする。今回の設計自体も暗黙の`.env`読み込みは行わない。

### 正常系の具体例

```python
settings = load_settings(testing=True)
assert isinstance(settings, Settings), "Validated Settings must be returned"
assert settings.database_url == expected_url
```

テスト用URLとして準備している値は`mysql+pymysql://example:example@127.0.0.1:3307/mondel_test`。これはテスト内のダミー入力で、接続には使わない。

`isinstance(settings, Settings)`は「返された値がSettings型か」を確認する。現在は`isinstance(None, Settings)`が偽なので最初の`assert`で止まる。DB URLの比較にはまだ到達しない。T009でSettingsが返るようになった後、選択したURL自体も検証する。

### 異常系の具体例

```python
monkeypatch.delenv("MONDEL_TEST_DATABASE_URL")
with pytest.raises(ValueError, match="MONDEL_TEST_DATABASE_URL"):
    load_settings(testing=True)
```

`delenv()`でテスト用URLを未設定にする。`with pytest.raises(...)`は、字下げした処理で指定した例外が起きることを期待する。`match`はエラーメッセージの照合条件で、ここでは原因の設定名が含まれるかを確認する。

現在は`None`が返り、例外は起きない。そのため`DID NOT RAISE ValueError`（期待したValueErrorが発生しなかった）でテストが失敗する。

期待した種類の例外が出ればテストは成功する。エラーなしで処理が終わったり、別の例外が出たりした場合は失敗する。テストの成功は「処理の成功」ではなく「期待した振る舞いとの一致」。

### 少ない関数で30ケースになる理由

`@pytest.mark.parametrize`は、指定した入力の組ごとに同じテスト関数を繰り返し実行する仕組み。例えば通常・テストの2モードと、不正URLの8パターンを組み合わせた関数は16ケースになる。`@`から始まる記述はデコレーターと呼び、ここではpytestへ実行条件を伝える。

### 実行コマンドと結果（2026-09-08）

リポジトリのルートから、統合ターミナルで次を実行した。

```bash
cd backend
uv run pytest tests/unit/test_config.py --tb=short -q
uv run pytest tests/unit/test_test_environment.py -q
uv run ruff check app tests/unit/test_config.py
cd ..
```

`--tb=short`は失敗箇所の表示を短くする指定、`-q`は出力量を抑える指定。どちらも確認内容を減らす指定ではない。`ruff check`はコードの問題を静的に検出するもので、処理の振る舞いを保証するテストとは異なる。

- 新規設定テスト：`30 failed`。返却型の不一致または期待した例外の未発生で失敗。収集・importエラーではない。
- 既存サンプル確認テスト：`1 passed`。
- Ruff：`All checks passed!`。
- DB・MLflowへは接続していない。

これをRed（期待する振る舞いがまだないことをテストで確認した状態）の証跡として残す。T008はRed確認までが目的なので完了、設定機能そのものはT009が終わるまで未完成。全テストが成功している状態ではない。

## 8. 今後の追記方針

- T009作成後：環境変数の読み込み・検証処理と、テストがGreenになるまでの流れ。
- T010以降：テスト用設定からDB接続へつながる場所と、接続の後片付け。
- 新しい概念は「目的 → 対象ファイル・関数 → 具体的なデータの変化 → 検証範囲」の順で残す。
