# GitHub spec-kit 使用手順書

## 目次

0. GitHub spec-kit の概念
1. constitutionの作成
2. specificationの作成
3. planの作成


## GitHub spec-kit の概念
spec-kit の中身は概念として以下のようなトップダウン関係がある

```txt
Constitution                    # プロジェクト全体の開発原則
    ↓
Specification                   # 何を作るかの仕様定義
  ├─ User Stories                   # 利用者視点の定義
  ├─ Functional Requirements        # システムが満たすべき具体的機能
  ├─ Success Criteria               # 完成したと言える客観的条件
  └─ Assumptions                    # 仕様を書くために置いた前提
  └─ Clarifications                 # 判断できない重要事項への質問、人間が答える
    ↓
Plan                            # specification で定義した仕様をどう実現するか
    ↓
Tasks                           # Planを実作業単位まで分解したもの
    ↓
Implementation                  # 実装
```

※開発過程で以下のまとまりで branch を切ると差分がわかりやすい（システムの土台そのものを作る場合）
- constitution
- specification
- plan
- tasks/implementation

> issue単位で変更を行う場合はこの限りではない。まとめて実行した方が自然。

## constitution の作成
vs code の チャット機能を使用する

チャット欄に以下を打ったあと、続いて自然言語で constitution を定義してチャットと相談しながら作成する

```txt
/speckit-constitution
```

ここでの目的は、開発をどのように進めるかを定義することである

## specification の作成
vs code の チャット機能を使用する

チャット欄に以下を打ったあと、続いて自然言語で specification を定義してチャットと相談しながら作成する

```txt
/speckit-specify
```

ここでの目的は、システムの仕様を決定することである

> 複数人で開発する際、 specs/002-???/spec.md のディレクトリ名が競合する可能性がある  
> その場合は、spec番号にissue番号を使うルールに変更する

### Clarify について
この工程では specification を読んで気になった点や、複数の解釈が残っている部分について、チャットで意思決定する工程  
自分が気になったことを質問するだけでなく、Spec Kit側もSpecificationを確認して、判断が必要な項目を提示する

イメージは以下
```txt
Specification初稿
        ↓
曖昧な部分を発見
        ↓
/speckit-clarify
        ↓
チャットで選択・回答
        ↓
回答をSpecificationへ反映
```

普通のチャットでも仕様の更新はできるが、clarify を使うと自分の気付けない曖昧点をあぶり出せる

## plan の作成

VS Code のチャット機能を使用する

チャット欄に以下を入力し、必要に応じて採用技術や制約を自然言語で補足する

```txt
/speckit-plan
```

ここでの目的は、Specificationで定義した「何を作るか」を、実装・検証できる技術設計へ変換することである。単に採用技術を決めるだけでなく、責務分担、データ構造、API、処理の流れ、例外処理、テスト方針まで具体化する。

実行環境によって構成は異なるが、一般的にはImplementation Plan、Research、Data Model、API Contract、Quickstartなどが生成される。生成物は完成版ではなく、レビューと修正を行うための初稿として扱う。

### 進め方

```txt
SpecificationとClarificationの確認
        ↓
/speckit-planを実行
        ↓
生成物を初稿として確認・必要に応じて保存
        ↓
設計内容を理解し、具体例や異常系で検証
        ↓
Specificationおよび生成物間の矛盾・不足を修正
        ↓
実装可能な状態になったらTasksへ進む
```

### 主な確認観点

- **仕様との対応**：要件や完了条件が設計に反映され、対象外の機能が入り込んでいないか
- **責務と境界**：画面、API、業務処理、データベース、外部サービスの担当範囲が明確か
- **データ設計**：エンティティ、関連、制約、正本、更新可能な情報と固定する情報が明確か
- **API設計**：入力、出力、バリデーション、HTTPステータス、ページング、取得不能時の表現が明確か
- **処理と整合性**：状態遷移、トランザクション、失敗時の扱い、再実行、同時実行を考慮しているか
- **技術とテスト**：採用理由が説明でき、必要なテストを適切な層へ分担できているか

### Plan完了の目安

- 主要な処理の流れと各構成要素の役割を説明できる
- Specification、Plan、Data Model、API Contractなどの用語と内容が整合している
- 正常系、異常系、境界値、同時実行時の振る舞いが実装・検証できる粒度になっている
- 未決定事項が整理され、Tasksへ分解できる

> Plan確認中に製品の振る舞いに関する判断が必要になった場合はSpecificationへ反映し、実現方法に関する判断はPlanへ記載する。

> 生成されたMarkdownは直接修正してよい。ただし、後続のTasksや実装の前提になるため、関連する成果物もあわせて更新する。理解・説明できない設計をそのまま確定しない。
