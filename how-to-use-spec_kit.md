# GitHub spec-kit 使用手順書

## 目次

0. GitHub spec-kit の概念
1. constitutionの作成
2. specificationの作成


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