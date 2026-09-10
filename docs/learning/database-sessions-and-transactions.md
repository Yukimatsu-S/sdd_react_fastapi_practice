# 学習ノート：DB Sessionとトランザクション

記録日：2026-09-10。第1〜8節はT010のRed時点の記録。第9節にT011の実装・Green確認を追記。

## 1. 今回の目的と全体像

[設定の学習ノート](testing-and-configuration.md)では接続先の文字列を検査した。今回は、実際のテスト用MySQLを使って、DB操作の確定・取り消し・後片付けを確認するテストを作る。

設定を読む → 接続を管理するEngineを準備する → SessionでDBを操作する → 成功ならcommit、失敗ならrollback → Sessionの利用を終了する、という順で理解する。

| 用語 | このプロジェクトでの意味 |
| --- | --- |
| Engine | SQLAlchemyの接続管理の入口。DBそのものではない |
| Session | PythonからDB操作やトランザクションを扱う窓口。ログイン状態のセッションとは別 |
| トランザクション | 複数のDB操作を、まとめて確定・取り消しする単位 |
| commit | DBの変更を確定する。Gitのコミットとは別 |
| rollback | 現在のトランザクションの未確定変更を取り消す |
| close | Sessionの利用を終了し、接続などのリソースを解放する。DBの削除ではない |

Sessionは必要に応じてEngineから接続を取得する。Sessionの生成と、ネットワーク接続の生成は同義ではない。[SQLAlchemy公式資料](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

原子性（Atomicity）は「全部を確定するか、全部を取り消すか」という性質。ただしAをcommitした後、別のトランザクションのBをrollbackしてもAは消えない。また、外部MLflowの操作までDBのrollbackで取り消せるわけではない。

## 2. ファイルの役割

| ファイル | 役割 |
| --- | --- |
| [tests/conftest.py](../../backend/tests/conftest.py) | pytestが見つける共通fixture。接続準備と検証用テーブルの後片付け |
| [tests/integration/test_database.py](../../backend/tests/integration/test_database.py) | DB操作の結果とSessionの終了を確認するテスト |
| [app/infrastructure/database.py](../../backend/app/infrastructure/database.py) | T011で作る処理の入口だけ。現時点では動作未実装 |

`conftest.py`はpytestがそのディレクトリ配下のテストに提供するfixtureを置くファイル。各テストからimportしなくても、引数にfixture名を書くとpytestが準備する。[pytest公式資料](https://docs.pytest.org/en/stable/how-to/fixtures.html)

単体テストはDB用fixtureを要求しないので、DB接続なしで実行できる。DB用fixtureが失敗したら準備エラーであり、意図したRedやスキップによる成功として扱わない。

## 3. 実行コマンドと設定の流れ

READMEに従ってテスト用MySQLを起動する。VS Codeでリポジトリを開き、統合ターミナルの作業場所がルートであることを`pwd`と`ls`で確認してから入力する。

```bash
cd backend
uv run --env-file .env.example pytest tests/integration/test_database.py -q --tb=short
```

- `uv run`：プロジェクトのPython環境で実行する。
- `--env-file .env.example`：今回は明示的にuvへサンプル設定を読み込ませる。アプリが自動でファイルを読むわけではない。
- `pytest`とファイルパス：このDBテストを実行する。
- `-q`：出力を少なくする。
- `--tb=short`：失敗箇所の説明を短く表示する。

環境変数を用意する機能はuvのもの。[uv公式資料](https://docs.astral.sh/uv/guides/scripts/)

`database_settings()`が`load_settings(testing=True)`を呼ぶ。さらにDBテスト独自の安全確認として、`mysql+pymysql`・`127.0.0.1`・`3307`・`mondel_test`以外は接続前に拒否する。別の接続先へ環境変数を上書きしている場合も、この制限に合わなければ止まる。

`database_engine()`がSQLAlchemy標準の`create_engine()`で接続の入口を準備し、`SELECT DATABASE()`で接続先を確認する。この準備はアプリ側の未実装の`build_engine()`に依存しない。

## 4. 検証用テーブルと後片付け

各テストで`probe_table()`が、`t010_probe_`にランダムなUUIDを付けた名前のInnoDBテーブルを作る。列は整数の主キー`id`だけ。

別の接続から変更を確認するため、SQLのTEMPORARY TABLEではなく、テストの間だけ利用する通常テーブルを使う。CREATE/DROP TABLEは検証するデータ操作のトランザクション外で行い、削除するのはそのfixture自身が作ったテーブルだけ。既存の製品テーブルやDB全体には触れない。

fixtureの`yield table`は「準備したテーブルをテストへ渡して、いったん待つ」という意味。テスト終了後に`finally`の処理へ進み、テーブルを削除する。テストが通常の例外で失敗した場合も後片付けする。ただしプロセス強制終了やDB切断なら後片付けが完了しない可能性はある。

Sessionの後片付けが先、テーブル削除が後になるようfixtureの依存関係を指定している。未実装のアプリ側が後片付けしなくても、テストfixtureは最後にSessionを閉じる。ただし成功判定はfixtureの後片付けより前に行うので、これで未実装を隠すことはない。

## 5. commitのケースをデータで追う

対象：`test_transaction_commits_all_rows()`。

1. 空の検証用テーブルと、SQLAlchemy標準機能で作ったSessionを受け取る。
2. `with transaction_scope(database_session) as session:`でアプリの共通処理を呼ぶ。
3. `session.execute(insert(probe_table).values(id=1))`でID 1を追加する。
4. 同様にID 2を追加する。
5. ブロックの中で別接続から読む。この時点では未確定なので`[]`を期待する。
6. `with`の範囲を抜ける。完成後なら共通処理がcommitするはず。
7. 別接続から読み直し、`[1, 2]`を期待する。

`insert(table)`は追加するSQLの組み立て、`.values(id=1)`は追加内容、`session.execute(...)`が実際の実行。`read_ids()`は別接続で`SELECT`し、IDの一覧を返す。

現時点の`transaction_scope()`は、次の通りSessionを渡すだけ。

```python
@contextmanager
def transaction_scope(session):
    yield session
```

`@contextmanager`は、この関数を`with`で使えるようにするPython標準の仕組み。`yield`で呼び出し元のブロックへ処理を渡し、ブロック終了時に続きを行う。しかし今は確定も取り消しも書いていないので、7で実際には`[]`が返り、`[1, 2]`との比較で失敗する。

## 6. rollbackのケースを追う

対象：`test_transaction_rolls_back_all_rows()`。2パターンある。

- ID 1を追加後、アプリの処理を想定したRuntimeErrorを出す。
- ID 1を追加後、同じ主キーのID 1をもう一度追加し、MySQLから重複エラーを受ける。

どちらも、共通処理がrollbackして元の例外を呼び出し元へ伝えることを期待する。テストでは例外確認後に、Sessionのトランザクションが終了したか、別接続から空に見えるか、元のSessionからも空に見えるかを確認する。

重要：別接続から`[]`が返るだけではrollbackした証拠にならない。未確定の変更も別接続から見えないため。`session.in_transaction()`（トランザクションが残っているか）も確認する。

現在はrollbackしていないため、`assert not database_session.in_transaction()`で失敗する。その後にfixtureが安全のため後片付けすることと、アプリの共通処理が正しくrollbackすることは別。

## 7. 残りのケースと現時点の限界

- Engine構築：設定どおりの同期Engineを返すこと。今は`None`なので失敗。
- Session生成：呼び出しごとに別のSessionを一つ返すこと。今は`None`をyieldするため失敗。
- 正常・異常終了時のSession解放：`close()`が呼ばれ、未確定データが確定されないこと。今はSessionの型の確認で止まり、closeの確認までは到達していない。
- commit時のエラー：`monkeypatch`でSessionのcommitを失敗する関数へ差し替え、rollbackと元の例外の伝達を期待する。今はcommit自体を呼ばないため、期待した例外が発生せず失敗。
- 同期の関数形式：`inspect`でasyncではなく通常のジェネレーター関数か確認。入口はその形で作ったので、この構造テストは既に成功する。

Sessionを返す関数の`next()`はyieldまで進める操作、`throw(error)`は待機中のyieldの位置へ例外を渡して異常終了を再現する操作。`closing(...)`はテスト終了時にジェネレーターを閉じる安全策。FastAPIへの登録や実際のHTTPリクエスト単位の再利用はT018以降であり、ここでは直接呼び出している。

## 8. 検証結果（T010）

- DB接続の事前確認：`PASS: (1, 'mondel_test', '8.0.46')`。
- 新規DBテスト：8 failed / 2 passed。準備エラー・importエラーはなし。2件の成功は接続fixtureの確認と同期関数形式の確認。
- 既存単体テスト：`uv run pytest tests/unit -q`で82 passed。
- 静的チェック：`uv run ruff check app tests`。複数のwithをまとめる指摘を修正し、All checks passed!を確認。
- 整形後のDBテスト再実行も8 failed / 2 passed。終了後にinformation_schemaを読み取り、現在のDBに`t010_probe_`で始まるテーブルが残っていないことを確認した。

T010は意図したRedまでを確認するタスク。DB共通処理の完成や全テスト成功を意味しない。T011ではこのテストを保持して、Engine・Session管理・commit/rollbackを実装する。

## 9. T011：同じテストを成功させる実装

対象は`app/infrastructure/database.py`。T010のテストを変更せず、3つの関数を実装した。ここからは現在の実装の説明。

### Engineを作る

`build_engine(settings)`が`create_engine(settings.database_url, connect_args=...)`の戻り値を返す。接続管理の準備であり、この時点では実接続しない。接続・読み取り・書き込みに5秒のタイムアウトを指定している。処理全体が5秒以内という意味ではない。

### Sessionを渡し、利用後に閉じる

```python
session = session_factory()
try:
    yield session
finally:
    session.close()
```

1. `next(request)`で`get_session()`の本体を進める。
2. `session_factory()`を呼び、新しいSessionを作る。関数を受け取るだけでなく、ここで`()`を付けて実行する。
3. `yield session`で呼び出し元へ渡し、一時停止する。
4. テストがSessionでDB操作を行う。
5. 正常終了の`next()`、異常終了を再現する`throw(error)`、ジェネレーターの`close()`によって終了処理へ進む。
6. `finally`がSessionを閉じる。未確定の変更を自動でcommitする処理はない。

前のテストでは`yield None`のため型確認で止まっていたが、今は本物のSessionが渡るので、closeの呼び出し記録と未確定データの確認まで進んで成功する。

### トランザクションを確定・取り消しする

```python
session.begin()
try:
    yield session
    session.commit()
except BaseException:
    session.rollback()
    raise
```

`begin()`はSessionのトランザクションを開始する。すでに開始済みなら新しく始められず拒否するため、この関数は新しいトランザクションの入口で使う。既存トランザクションの中から呼ぶ設計ではない。`begin()`をtryの外に置くことで、開始できなかった場合に呼び出し元のトランザクションを勝手にrollbackしない。

正常時：`begin()` → `yield`でテストのブロックへ → ID 1・2を追加 → ブロック終了で再開 → `commit()` → 別接続から`[1, 2]`が見える。

異常時：`yield`先のブロックで例外 → その例外がyieldの位置へ伝わる → commitには進まずexceptへ → `rollback()` → `raise`で元の例外を伝える。

`raise`だけの行は、受け取って処理中の例外を再び伝える書き方。`BaseException`は通常のエラーに加えて中断やジェネレーター終了も含む例外の基底型。ここでは後片付け後に必ず再送出し、失敗や中断を成功として飲み込まない。

commit自体もtryの中に置いているため、テストで差し替えたcommitが例外を出した場合もrollbackへ進む。transaction_scopeはSessionを閉じず、その所有者であるget_sessionやテストfixtureが閉じる。

注意：ネットワーク切断でDB側の確定結果が不明な場合や、rollback自体が失敗する場合まで、このテストで保証しているわけではない。今回のcommit失敗テストは本物のcommitを行う前に例外を出す模擬である。

### 実行コマンドと結果

`backend`を作業場所として実行。

```bash
uv run --env-file .env.example pytest tests/integration/test_database.py -q --tb=short
uv run pytest tests/unit -q
uv run ruff check app tests
```

結果：10 passed（T010のテスト変更なし）、82 passed、All checks passed!。

続けて`uv run --env-file .env.example pytest -q`で全バックエンドテストをまとめて実行し、92 passedを確認。終了後にMySQLのテーブル情報を読み取り、`t010_probe_`で始まる検証用テーブルが残っていないことも確認した。

これで直接呼び出した場合のEngine構築、Sessionの分離・正常／異常終了時の解放、commit、rollback、commit失敗時の取り消しを確認した。実際のFastAPIリクエストとの結び付けはT018で行う。

### 読み方の統一

学習中の混乱を減らすため、今後の関数差し替えは理由がなければ`monkeypatch.setattr(対象, "属性名", 置き換えるもの)`の3引数に統一する。T011では既存テストを保持するため、過去の別表記の一括変更は行っていない。
