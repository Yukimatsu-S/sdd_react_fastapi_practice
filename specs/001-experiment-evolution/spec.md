# Feature Specification: Mondel Initial MVP

**Feature Branch**: `chore/create-specification`

**Created**: 2026-09-01

**Status**: Ready for Planning

**Input**: User description: "機械学習モデルの改善を繰り返す開発者が、Evolution Stepの目的、仮説、派生元、変更点、実行結果、およびLineageを後から確認できる初期MVPを定義する。"

## Clarifications

### Session 2026-09-01

- Q: 外部で実行済みのRunの情報は、どの方法でこの製品に取り込みますか？ → A: MLflowからRun、実測条件、評価指標、データセット識別情報を読み込む。
- Q: 本製品とMLflowは学習処理についてどのように責務を分けますか？ → A: 学習処理は本製品の外部で行い、外部の学習コードが実行結果をMLflowに記録する。本製品から学習を開始・停止・再実行しない。
- Q: 初期MVPで連携する実験管理ツールはどれにしますか？ → A: MLflowのみを対象にする。
- Q: MLflowから取得した実測条件と評価指標は、どのように扱いますか？ → A: 実測条件は取得できるすべてをEvolution Step詳細に表示する。評価指標はaccuracyが最大となったstepに記録された値を詳細で表示し、自動結果差分はaccuracyだけを対象とする。
- Q: 手動で記録する変更内容とMLflowから取得する実測条件をどのように区別しますか？ → A: 前者は変更の意図・予定・定性的説明、後者は実行済みRunのParametersとする。
- Q: 実行結果Runの紐付け後にEvolution Step情報を編集できますか？ → A: 目的、仮説、変更内容はいつでも編集でき、各編集は変更前後、編集日時、時系列順を確認できる全履歴として保持する。
- Q: RunとLineageの関係にはどの制約を設けますか？ → A: Evolution Stepの派生元Runと実行結果Runは各0件または1件、Runを実行結果として紐付けられるEvolution Stepは0件または1件とする。Runは複数の後続Evolution Stepの派生元として参照でき、重複・同一指定・循環する紐付けは拒否する。
- Q: Runの紐付けを変更または解除できますか？ → A: 派生元Runと実行結果RunはEvolution Step登録後も変更または解除できる。対象Evolution Stepだけを更新し、過去の紐付けは変更履歴に保持する。変更後は現在の紐付けでLineageを再構成する。
- Q: Delete機能を初期MVPに含めますか？ → A: 含めない。Evolution Stepの物理削除、アーカイブ、Lineageからの任意のEvolution StepまたはRunの直接除外は対象外とする。
- Q: データセットの変更は、初期MVPでどのように記録・比較しますか？ → A: データセット名とバージョンなどの識別情報を取得し、差分比較する。

### Session 2026-09-02

- Q: 目的、仮説、および任意の変更内容では、空文字や空白だけの入力をどのように扱いますか？ → A: 目的と仮説は空白以外の文字を1文字以上必須とする。変更内容は未設定にできるが、入力する場合は空白以外の文字を1文字以上必須とし、空文字または空白だけの入力は拒否する。登録済みの変更内容は未設定へ戻せる。

### Session 2026-09-03

- Q: Evolution Step一覧には、識別情報に加えてどこまで比較結果を表示しますか？ → A: 目的、仮説、派生元Run、実行結果Run、作成日時、更新日時に加え、比較可否、実測条件の変更件数、最良accuracyとその増減、およびデータセットの変更状態を要約表示する。具体的な実測条件差分とデータセット識別情報の差分は比較表示で確認し、変更なしと比較情報なしを区別する。
- Q: accuracyの記録値と画面表示の単位をどのように統一しますか？ → A: 外部の学習コードはaccuracyを0以上1以下の比率としてMLflowへ記録し、本製品は取得した数値を保持する。画面では最良accuracyを百分率、その増減をパーセントポイントで表示する。
- Q: 学習中のRunを紐付けた場合、Snapshotをいつ確定しますか？ → A: Runの参照関係は学習中でも保存し、Snapshotを未確定として表示する。Evolution Step詳細を開いた時に対象Runの状態を自動確認し、RunがFINISHED、FAILED、またはKILLEDの終了状態なら、その時点のParameters、最良stepのMetrics、データセット識別情報などを一度だけ取り込んでSnapshotを確定する。RUNNINGまたはSCHEDULEDなら未確定のままとする。確定後のSnapshotは更新せず、Run名と現在状態だけを表示情報として同期する。
- Q: アプリ内で選択するRun候補は、どのように検索・表示しますか？ → A: MLflowの有効なExperimentに属する削除されていないRunを、開始日時の新しい順で20件ずつ取得する。候補にはRun ID、Run名、MLflow ExperimentのIDと名前、状態、開始日時、終了日時を表示する。Run名の大文字小文字を区別しない部分一致で検索でき、同名RunはRun IDで区別する。
- Q: Dataset Inputの差分は、どの単位と表現で示しますか？ → A: 用途と名前が同じDataset Inputを対応付け、digestまたは取得済みのsource識別情報が異なる場合は`changed`とする。片方にだけ対応候補がある場合は`parent_only`または`result_only`とし、データ行の追加・削除を意味する`added`または`removed`とは表現しない。いずれかのRunにDataset Inputが一件も記録されていない場合は比較情報なしとする。
- Q: Lineageは、選択したEvolution Stepを基準にどの順序と境界で表示しますか？ → A: 選択したEvolution Stepを中心とし、祖先と子孫をそれぞれ直近の世代から外側へ表示する。同じ世代の子孫はEvolution Step ID順とする。派生元Runが未設定ならそのStepより上流は存在せず、派生元Runが設定されていてもそれを実行結果とするEvolution Stepが登録されていなければ、そのRunを追跡可能範囲の上流境界として表示する。
- Q: Metricはどの時点の値をSnapshotへ保存・表示しますか？ → A: まずMetric名とstepが同じ複数の記録を最新timestampの値に一本化し、最新timestampも同じ場合は最大値を採用する。一本化後のaccuracyから最大値を求め、その値が複数stepにある場合は最小stepを選ぶ。そのstepに記録された各Metricだけを保存して詳細表示し、全stepのMetric履歴は保存・表示しない。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evolution Stepを定義してRunを紐付ける (Priority: P1)

機械学習モデルを改善する開発者として、Evolution Stepの目的と仮説を記録し、必要に応じて派生元のRunと変更内容を指定したい。外部の学習コードがMLflowに記録した結果RunをEvolution Stepに紐付け、何を検証した改善工程なのかを結果とともに参照できるようにするためである。

**Why this priority**: 目的・仮説・変更内容と実行結果を一つのEvolution Stepとして残すことが、比較や振り返りの基礎となるためである。

**Independent Test**: 目的と仮説を入力し、任意で派生元Runと変更内容を指定して登録する。MLflowから取得したRunを選択して紐付け、Evolution Stepの詳細に入力内容とRunの情報が表示されれば価値を確認できる。

**Acceptance Scenarios**:

1. **Given** 開発者が新しいEvolution Stepをまだ登録していない状態、**When** Evolution Stepの目的と仮説を入力して登録する、**Then** 新しいEvolution Stepが作成され、目的と仮説を詳細で確認できる。
2. **Given** 利用者がMLflowから取得したRunを確認できる状態、**When** 新しいEvolution Stepの派生元としてRunを選択し、変更内容を記録して登録する、**Then** Evolution Stepには派生元Runと変更内容が関連付けられる。
3. **Given** 目的と仮説を持つEvolution Stepが登録済みであり、MLflowから取得したRunがある状態、**When** 利用者がそのRunをEvolution Stepの実行結果として選択して紐付ける、**Then** Evolution Stepに関連するRun情報、実測条件、評価指標、データセット識別情報を後から確認できる。
4. **Given** 実行結果Runが未設定のEvolution Stepと、外部で学習を実行済みのRunがある状態、**When** 開発者がそのRunをEvolution Stepの実行結果として紐付ける、**Then** Evolution Stepは実行結果Runを一件だけ持つ。
5. **Given** あるEvolution Stepの実行結果Runが登録済みの状態、**When** 開発者がそのRunを派生元として複数の新しいEvolution Stepを登録する、**Then** 各新しいEvolution Stepは同じRunを派生元として参照できる。
6. **Given** 実行結果Runの紐付け後に、Evolution Stepの目的、仮説、または変更内容が複数回編集されている状態、**When** 利用者が変更履歴を確認する、**Then** 各編集の対象項目、編集前の内容、編集後の内容、編集日時を時系列順に確認できる。
7. **Given** あるRunがすでに別のEvolution Stepの実行結果として紐付けられている状態、**When** 利用者が同じRunを別のEvolution Stepの実行結果として紐付けようとする、**Then** 紐付けは完了せず、そのRunがすでに使用されていることを確認できる。
8. **Given** あるRunがEvolution Stepの派生元として指定されている状態、**When** 利用者が同じRunをそのEvolution Stepの実行結果として紐付けようとする、**Then** 紐付けは完了せず、同じRunを両方に指定できないことを確認できる。
9. **Given** 複数世代のLineageが登録されている状態、**When** 利用者が祖先Runを子孫側のEvolution Stepの結果として紐付けるなど、循環を作る操作を行う、**Then** 紐付けは完了せず、循環するLineageを作成できないことを確認できる。
10. **Given** Evolution Stepに派生元Runが設定されている状態、**When** 利用者が派生元Runを別のRunへ変更する、**Then** 新しい派生元Runが保存され、変更前と変更後のRunおよび変更日時を履歴で確認できる。
11. **Given** Evolution Stepに派生元Runが設定されている状態、**When** 利用者が派生元Runとの紐付けを解除する、**Then** Evolution Stepは派生元Runが未設定の起点となり、解除前のRunと変更日時を履歴で確認でき、現在の紐付けをもとにLineageが再構成される。
12. **Given** Evolution Stepに実行結果Runが紐付いている状態、**When** 利用者が実行結果Runを別の未使用Runへ変更する、**Then** 新しい実行結果Runが保存され、変更前と変更後のRunおよび変更日時を履歴で確認できる。
13. **Given** Evolution Stepに実行結果Runが紐付いている状態、**When** 利用者が実行結果Runとの紐付けを解除する、**Then** Evolution Stepは実行結果Runが未設定の状態になり、解除前のRunと変更日時を履歴で確認できる。
14. **Given** 変更前の実行結果Runを派生元として参照する後続Evolution Stepがある状態、**When** 利用者が実行結果Runを変更または解除する、**Then** 後続Evolution Stepの派生元Runは自動変更されず、元のRunを引き続き参照する。
15. **Given** Runの変更によってLineageに循環が発生する状態、**When** 利用者がRunの変更を確定しようとする、**Then** 変更は完了せず、循環するLineageを作成できないことを確認できる。
16. **Given** 利用者がEvolution Stepを登録または編集している状態、**When** 目的または仮説に空文字か空白だけを入力する、または変更内容を入力済みとして空文字か空白だけを指定する、**Then** 保存は完了せず、該当する入力項目の修正が必要であることを確認できる。
17. **Given** MLflow上でRUNNINGまたはSCHEDULEDのRunが存在する状態、**When** 利用者がそのRunをEvolution Stepへ紐付ける、**Then** Runとの参照関係は保存され、Snapshot未確定として確認できる。
18. **Given** Snapshot未確定のRunがMLflow上でRUNNINGまたはSCHEDULEDの状態、**When** 利用者がEvolution Step詳細を開く、**Then** Runの現在状態と名前が同期され、Snapshotは未確定のまま表示される。
19. **Given** Snapshot未確定のRunがMLflow上でFINISHED、FAILED、またはKILLEDの状態、**When** 利用者がEvolution Step詳細を開く、**Then** Runの現在情報が取得され、Snapshotが一度だけ確定される。
20. **Given** MLflowに21件以上のRunが存在する状態、**When** 利用者がRun選択欄を開く、**Then** 開始日時の新しい順で最初の20件を確認でき、続きがある場合だけ次の候補群を取得できる。
21. **Given** 同じRun名を持つ複数のRunが存在する状態、**When** 利用者がRun候補を確認する、**Then** MLflow Experiment、状態、実行日時、およびRun IDによって各Runを区別して選択できる。

---

### User Story 2 - Evolution Stepの全体像を確認する (Priority: P2)

機械学習モデルを改善する開発者として、登録済みのEvolution Stepを一覧で確認し、各Stepの意図と結果の変化を把握したうえで、関心のあるEvolution Stepの比較または詳細を開きたい。過去の改善工程を探し、改善の結果を素早く振り返るためである。

**Why this priority**: Evolution Stepが蓄積された後に、個別の検証結果へ到達するための入口となるためである。

**Independent Test**: 複数の登録済みEvolution Stepを一覧で確認し、目的、仮説、関連するRun、比較可否、実測条件の変更件数、accuracyの変化、およびデータセットの変更状態から任意のEvolution Stepを選び、比較または詳細を確認できれば価値を確認できる。

**Acceptance Scenarios**:

1. **Given** 複数のEvolution Stepが登録済みの状態、**When** 開発者がEvolution Step一覧を表示する、**Then** 各Evolution Stepの目的、仮説、派生元Run、実行結果Run、作成日時、更新日時、および比較結果の要約を確認してEvolution Stepを選択できる。
2. **Given** 一覧にEvolution Stepが表示されている状態、**When** 開発者がEvolution Stepを一つ選択する、**Then** そのEvolution Stepの目的、仮説、関連するRun情報、実測条件、評価指標、データセット識別情報を確認できる。
3. **Given** 派生元Runと実行結果Runを持つEvolution Stepが一覧に表示されている状態、**When** 開発者が比較結果の要約を確認する、**Then** 実測条件の変更件数、各Runの最良accuracyとその増減、およびデータセットが変更あり・変更なし・比較情報なしのいずれであるかを確認できる。
4. **Given** 派生元Runまたは実行結果Runが未設定で比較できないEvolution Stepがある状態、**When** 開発者がEvolution Step一覧を表示する、**Then** 数値を変更なしとして表示せず、比較できない状態と理由を確認できる。
5. **Given** Evolution Stepに紐付くRunの名前がMLflow上で変更されている状態、**When** 開発者がそのEvolution Stepの詳細を開く、**Then** 保存済み詳細が表示された後にRun情報が自動同期され、現在のRun名、状態、および同期日時を確認できる。確定済みのParameters、最良stepのMetrics、およびデータセット識別情報は変更されない。
6. **Given** Evolution StepにRunが紐付いておりMLflowへ接続できない状態、**When** 開発者がそのEvolution Stepの詳細を開く、**Then** 保存済み詳細の表示は失敗せず、最後に同期できたRun名、状態、同期日時、Snapshotの確定状態、および同期できなかったことを確認できる。

---

### User Story 3 - 派生元との差分を振り返る (Priority: P3)

機械学習モデルを改善する開発者として、派生元Runと現在のEvolution Stepについて、何を変更し、評価結果がどう変化したかを確認したい。改善の仮説が結果に結び付いたかを判断するためである。

**Why this priority**: モデルの改善過程を理解する製品目的に直接つながるが、Evolution Stepの作成と実行結果Runの紐付けができた後に価値を発揮するためである。

**Independent Test**: 派生元Runと実行結果Runを持つEvolution Stepを開く。派生元と実行結果Runの実測条件差分、accuracy差分、データセット識別情報の差分を確認できれば価値を確認できる。

**Acceptance Scenarios**:

1. **Given** 派生元Runと実行結果Runの実測条件が記録されている状態、**When** 開発者が実測条件差分を確認する、**Then** 派生元から追加、変更、削除された実測条件を区別して確認できる。
2. **Given** 派生元Runと実行結果Runの両方にaccuracyが0以上1以下の比率として複数回記録されている状態、**When** 利用者が結果差分を確認する、**Then** 各Runの最大accuracyを百分率、両者の増減をパーセントポイントで確認できる。
3. **Given** 派生元Runが指定されていないEvolution Stepを開いている状態、**When** 開発者が差分を確認しようとする、**Then** 比較対象がないことを明確に確認できる。
4. **Given** 派生元Runと実行結果Runに同じ用途と名前のDataset Inputが記録されている状態、**When** 開発者がデータセット識別情報の差分を確認する、**Then** digestまたはsource識別情報に相違があるDataset Inputだけを`changed`として確認できる。
5. **Given** 派生元Runまたは実行結果Runのどちらかにaccuracyが記録されていない状態、**When** 利用者が結果差分を確認する、**Then** accuracy差分は算出されず、比較できない理由を確認できる。
6. **Given** 両方のRunにDataset Inputが記録され、同じ用途と名前の対応候補が片方にだけ存在する状態、**When** 開発者がデータセット識別情報の差分を確認する、**Then** その候補が派生元Runだけにある場合は`parent_only`、実行結果Runだけにある場合は`result_only`として確認できる。
7. **Given** 派生元Runまたは実行結果RunのどちらかにDataset Inputが一件も記録されていない状態、**When** 開発者がデータセット識別情報の差分を確認する、**Then** Datasetが同一または変更されたとは判定されず、比較情報がないことを確認できる。
8. **Given** 一つのRunで同じMetric名とstepの記録が複数あり、一本化後の最大accuracyも複数stepにある状態、**When** 開発者がEvolution Step詳細で評価指標を確認する、**Then** 同一Metric・同一stepでは最新timestampの値、最新timestampも同じ場合は最大値が採用され、その後に最大accuracyへ最初に到達した最小stepと、そのstepに記録された各Metricだけを確認できる。

---

### User Story 4 - Lineageを確認する (Priority: P4)

機械学習モデルを改善する開発者として、選択したEvolution Stepを中心に、そこへ至るすべての祖先と、そこから派生したすべての子孫を確認したい。改善の流れを両方向へ追跡するためである。

**Why this priority**: 個々の比較だけでは見えない改善の経緯を把握できるが、Lineageを構成するEvolution Stepがあることを前提とするためである。

**Independent Test**: 複数世代のLineageを持つEvolution Stepを選択し、祖先と子孫を順序付きの関係として確認できれば価値を確認できる。

**Acceptance Scenarios**:

1. **Given** 複数世代にわたるLineageを持つEvolution Stepが登録済みの状態、**When** 開発者が任意のEvolution StepのLineageを確認する、**Then** 当該Evolution Stepを中心として、すべての祖先を直近の世代から上流へ確認できる。
2. **Given** 複数世代にわたる枝分かれしたLineageが登録済みの状態、**When** 開発者が任意のEvolution StepのLineageを確認する、**Then** すべての子孫を直近の世代から下流へ確認でき、同じ世代の分岐と各子孫の直前のEvolution Stepを識別できる。
3. **Given** 派生元を持たないEvolution Stepを開いている状態、**When** 開発者がLineageを確認する、**Then** そのEvolution Stepが起点であることを確認できる。
4. **Given** Mondel内のEvolution Stepに実行結果として紐付いていないMLflow Runを派生元とするEvolution Stepがある状態、**When** 利用者がそのEvolution StepのLineageを確認する、**Then** 当該Runが追跡可能範囲の上流境界として表示され、それより前のEvolution Stepが登録されていないことを確認できる。

### Edge Cases

- 目的または仮説が未入力、空文字、または空白だけの状態で登録しようとした場合、登録を完了せず、入力が必要な項目を開発者に示す。任意の変更内容も、入力する場合は空文字または空白だけの値を拒否する。
- 指定した派生元Runまたは実行結果Runに実測条件がない場合、利用可能な情報だけを表示し、比較できない項目を明示する。
- 派生元Runまたは実行結果Runにaccuracyがない場合、accuracy差分を算出せず、比較できない理由を示す。
- 指定した派生元Runまたは実行結果Runにデータセット識別情報がない場合、利用可能な情報だけを表示し、データセットを比較できないことを示す。
- MLflowから取得したRunを紐付けようとしたが必要な情報を取得できない場合、紐付けを完了せず、利用者に再試行または別のRunの選択を促す。
- Run候補の取得時、または保存されていないRunの初回紐付け時にMLflowから必要なRun情報を取得できない場合、利用者に取得できないことを示し、再試行を促す。
- Evolution Stepの詳細表示時にMLflowへ接続できない場合、Run同期だけを失敗として扱い、保存済みの詳細、比較、およびLineageの閲覧を妨げない。
- Snapshot未確定のRunがFAILEDまたはKILLEDになった場合も、その時点までに取得できる情報でSnapshotを確定し、実行状態を明示する。
- Snapshot確定後に同じRun IDへの記録が再開された場合、現在状態とRun名は同期するが、確定済みSnapshotは更新しない。
- すでに別のEvolution Stepの実行結果RunであるRunを実行結果として紐付けようとした場合、紐付けを完了せず、その理由を示す。
- 同じRunを同じEvolution Stepの派生元Runと実行結果Runの両方に指定しようとした場合、紐付けを完了せず、その理由を示す。
- 新しい紐付けによってLineageに循環が生じる場合、紐付けを完了せず、その理由を示す。
- 別のEvolution Stepですでに実行結果Runとして使用されているRunへ変更しようとした場合、変更を完了せず、その理由を示す。
- 同じRunを同じEvolution Stepの派生元Runと実行結果Runに指定する変更、またはLineageに循環を生じさせる変更をしようとした場合、変更を完了せず、その理由を示す。
- 実行結果Runを変更した場合、他のEvolution Stepが派生元Runとして参照するRunは自動変更しない。実行結果Runを解除したEvolution Stepは、実行結果Runが未設定の状態になる。
- Evolution Stepの保存後に利用を終了して再開した場合、保存済みのEvolution Step、Run、実測条件、評価指標、データセット識別情報、変更内容、変更履歴、およびLineageを確認できる。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: システムは、登録済みのEvolution Stepについて、目的、仮説、派生元Run、実行結果Run、作成日時、および更新日時を一覧で表示し、利用者が各Evolution Stepを識別して選択できるようにしなければならない。一覧には比較可否、実測条件の変更件数、比較可能な場合の各Runの最良accuracyとその増減、およびデータセットの変更状態を要約表示し、変更なしと比較情報なしを区別しなければならない。
- **FR-002**: システムは、利用者が空白以外の文字を1文字以上含むEvolution Stepの目的と仮説を、必須情報として登録できるようにしなければならない。
- **FR-003**: システムは、利用者が新しいEvolution Stepに対して派生元となる既存Runを任意で指定できるようにしなければならない。
- **FR-004**: システムは、利用者が派生元から追加、変更、または削除する意図・予定・定性的説明を、任意の変更内容としてEvolution Stepごとに記録できるようにしなければならない。変更内容を入力する場合は空白以外の文字を1文字以上必要とし、空文字または空白だけの値を拒否しなければならない。
- **FR-005**: システムは、利用者が登録済みEvolution Stepの目的、仮説、派生元、変更内容、関連するRun情報、実測条件、評価指標、およびデータセット識別情報を詳細で確認できるようにしなければならない。
- **FR-006**: システムは、MLflowの有効なExperimentに属する削除されていないRunを候補として取得し、Run ID、Run名、MLflow ExperimentのIDと名前、状態、開始日時、および終了日時を表示して利用者が選択できるようにしなければならない。
- **FR-007**: システムは、利用者が取得済みのRunを選択し、登録済みのEvolution Stepの実行結果として手動で一件だけ紐付けられるようにしなければならない。実行結果Runが未設定のEvolution Stepも登録できなければならない。
- **FR-008**: システムは、一つのRunを実行結果として紐付けられるEvolution Stepを0件または1件に制限し、すでに別のEvolution Stepの実行結果RunであるRunを紐付けようとした場合は拒否しなければならない。
- **FR-009**: システムは、アプリ内のEvolution Stepに実行結果として紐付いていないMLflow Runを含め、一つのRunを複数の後続Evolution Stepの派生元として参照できるようにしなければならない。
- **FR-010**: システムは、同じRunを同じEvolution Stepの派生元Runと実行結果Runの両方に指定すること、および新しい紐付けによってLineageに循環を生じさせることを拒否し、その理由を利用者に示さなければならない。
- **FR-011**: システムは、Evolution Stepに手動で紐付けたRunについて、Run IDとの参照関係を直ちに記録し、Snapshot確定後は取得した実測条件、評価指標、およびデータセット識別情報を後から確認できるようにしなければならない。
- **FR-012**: システムは、派生元Runが指定されたEvolution Stepについて、MLflowから取得できるすべての実測条件を表示し、派生元Runと実行結果Runの追加、変更、削除を比較表示できるようにしなければならない。
- **FR-013**: システムは、各RunのMetric履歴について、同じMetric名とstepを持つ記録が複数ある場合は最新timestampの値に一本化し、最新timestampも同じ場合は最大値を採用しなければならない。その後、一本化済みaccuracyが最大となる最小stepを最良stepとして選び、そのstepに記録された各Metricの名前と値だけをEvolution Step詳細で表示しなければならない。当該stepに記録されていないMetricを別stepの値で補完せず、全stepのMetric履歴を保存または表示してはならない。
- **FR-014**: システムは、派生元Runと実行結果Runの両方にaccuracyが記録されている場合、FR-013で一本化した各Runのaccuracyの最大値を最良accuracyとして百分率で表示し、実行結果Runの最良accuracyから派生元Runの最良accuracyを引いた増減をパーセントポイントで表示しなければならない。最大accuracyが複数stepにある場合は最小stepを最良stepとし、保存する値はMLflowから取得した0以上1以下の比率を維持しなければならない。
- **FR-015**: システムは、accuracy以外の評価指標について、最大化・最小化の判定、最良値の自動選択、および自動的な結果差分の算出を行ってはならない。利用者が比較対象の評価指標を選択する機能も提供してはならない。
- **FR-016**: システムは、派生元Runが指定されたEvolution Stepについて、用途と名前が同じDataset Inputを対応付け、digestおよび取得済みのsource識別情報を比較しなければならない。識別情報が異なる対応候補は`changed`、派生元Runだけにある候補は`parent_only`、実行結果Runだけにある候補は`result_only`として差分だけを表示し、これらをDataset内のデータ行の追加・削除として表現してはならない。いずれかのRunにDataset Inputが一件も記録されていない場合は、変更なしではなく比較情報なしとして表示しなければならない。
- **FR-017**: システムは、利用者が選択したEvolution Stepを中心として、すべての祖先と子孫をそれぞれ直近の世代から外側へ確認できるようにしなければならない。各Evolution Stepについて選択対象からの距離と直前のEvolution Stepを識別できるようにし、同じ世代の子孫はEvolution Step IDの昇順で表示しなければならない。派生元Runが未設定なら上流探索を終了し、派生元Runを実行結果とするEvolution Stepが登録されていない場合は、そのRunを追跡可能範囲の上流境界として表示して探索を終了しなければならない。
- **FR-018**: システムは、Evolution Step、関連するRun情報、実測条件、評価指標、データセット識別情報、変更内容、変更履歴、およびLineageを利用終了後も保持し、後から再確認できるようにしなければならない。
- **FR-019**: システムは、派生元がない、実行結果Runが未設定である、Snapshotが未確定である、accuracyが記録されていない、比較可能な情報が不足している、またはMLflowからRun情報を取得できない場合に、その状態と理由を利用者に明確に示さなければならない。
- **FR-020**: システムは、利用者がEvolution Stepの目的、仮説、および変更内容をいつでも編集し、任意の変更内容を未設定へ戻せるようにしなければならない。編集後の目的、仮説、および入力済みの変更内容は、空白以外の文字を1文字以上含まなければならない。
- **FR-021**: システムは、実行結果Runの紐付け後に行われた各編集について、対象項目、編集前と編集後の内容、編集日時を変更履歴として保持し、編集日時の順に確認できるようにしなければならない。
- **FR-022**: システムは、利用者がEvolution Step登録後も派生元Runを変更または解除し、実行結果Runを別の未使用Runへ変更または解除できるようにしなければならない。これらはEvolution Stepの削除ではなくUpdateとして扱わなければならない。
- **FR-023**: システムは、派生元Runまたは実行結果Runの変更・解除について、変更対象、変更前のRun、変更後のRun、変更日時を変更履歴として保持し、過去の紐付けを確認できるようにしなければならない。
- **FR-024**: システムは、Runの変更・解除後、現在の紐付けをもとにLineageを再構成しなければならない。更新は対象のEvolution Stepだけに適用し、他のEvolution Stepの派生元Runまたは実行結果Runを自動変更してはならない。
- **FR-025**: システムは、MLflow上でRUNNINGまたはSCHEDULEDのRunをEvolution Stepへ紐付け、Snapshot未確定のRun参照として保持できなければならない。
- **FR-026**: システムは、Evolution Step詳細表示時に、紐付いたRunの現在の名前と状態を自動的に同期しなければならない。Snapshot未確定のRunがFINISHED、FAILED、またはKILLEDである場合は、その時点のRun情報、Parameters、最良stepのMetrics、およびデータセット識別情報を取得し、Snapshotを一度だけ確定しなければならない。
- **FR-027**: システムは、確定済みSnapshotのParameters、最良stepのMetrics、データセット識別情報、確定時の実行状態、実行日時、およびその他のSnapshot情報を更新してはならない。現在のRun名、状態、実行日時、および最終同期日時だけをRun Reference上の変更可能な表示情報として扱い、それらの同期によって比較結果またはLineageが変化してはならない。
- **FR-028**: システムは、Evolution Step詳細表示時のRun同期に失敗した場合でも、最後に同期できたRun名、状態、同期日時、およびSnapshotの確定状態を含む保存済み情報を表示し、同期できなかったことを利用者に示さなければならない。Runを初めて紐付ける際にMLflow上の存在を確認できない場合は、紐付けを完了してはならない。
- **FR-029**: システムは、Run候補を開始日時の降順、同一開始日時ではRun IDの昇順で20件ずつ返し、続きがある場合は次の候補群を取得するための値を提供しなければならない。利用者はRun名の大文字小文字を区別しない部分一致によって候補を任意で検索できなければならない。

### Key Entities

- **Mondel**: 機械学習モデルの改善工程と系譜を記録・追跡する本製品の名称。
- **Evolution Step**: 派生元Runから実行結果Runへ進む一回の改善工程。改善の目的と仮説を表し、派生元Runを0件または1件、手動で紐付ける実行結果Runを0件または1件持つ。実行結果Runが未設定の状態でも登録でき、両方のRunは登録後に変更または解除できる。
- **Run**: 外部の学習コードがMLflowに記録した一回の学習の記録。実行状態、実測条件、評価指標、およびデータセット識別情報を持つ。
- **Run Reference**: Evolution StepとMLflow RunをRun IDで結ぶ参照情報。Snapshotが未確定でも保持できる。Run IDを不変の識別子とし、現在のRun名、現在状態、実行日時、および最終同期日時を変更可能な表示情報として持つ。
- **Run Snapshot**: RunがFINISHED、FAILED、またはKILLEDになったことを確認した時点で一度だけ保存するParameters、最良accuracyと最良step、そのstepのMetrics、データセット識別情報、およびその他の実行情報。比較と振り返りの根拠として再利用し、確定後は更新しない。
- **変更内容**: 利用者が記録する、派生元から追加、変更、または削除する意図・予定・定性的説明。
- **実測条件**: MLflowに記録された、実行済みRunの名前と値を持つ条件。取得できるすべてを表示し、派生元との差分として追加、変更、削除を識別できる。
- **評価指標**: MLflowから取得する、学習結果を評価する名前と値を持つ測定値。最大accuracyへ最初に到達した最小stepに記録されたものだけを表示する。自動結果差分はaccuracyだけを対象とし、accuracy以外の最良値は自動選択しない。
- **Dataset Input／データセット識別情報**: Runで使用したDatasetとその用途をMLflowへ記録した入力情報、およびDatasetの名前、digest、sourceなどの識別情報。比較結果はRun間の記録と識別情報の相違を示し、Dataset内のデータ行単位の増減は示さない。
- **Lineage**: 複数のEvolution StepをRunの派生関係で結んだ、循環のない系譜。選択したEvolution Stepを中心として、祖先方向と子孫方向へ世代順にたどるために用いる。保存済みの現在の紐付けから導出し、派生元Runを実行結果とするEvolution Stepが登録されていない場合は、そのRunを追跡可能範囲の上流境界とする。
- **変更履歴**: Evolution Stepの目的、仮説、変更内容、派生元Run、または実行結果Runの各編集について、変更対象、変更前と変更後の内容またはRun、編集日時を表す記録。Runの解除では変更後のRunを未設定として記録する。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 利用者は、目的と仮説を入力して新しいEvolution Stepを定義し、外部で実行済みのRunを実行結果として紐付けるまでを 3 分以内に完了できる。
- **SC-002**: 派生元Runと実行結果Runを持つEvolution Stepでは、利用者は詳細を開いてから 1 分以内に実測条件差分、最良accuracy、およびaccuracy差分を確認できる。
- **SC-003**: 複数世代のLineageを持つEvolution Stepでは、利用者は選択したEvolution Stepのすべての祖先とすべての子孫を、派生順序とともに 1 分以内に識別できる。
- **SC-004**: 保存済みEvolution Stepを利用終了後に再確認する検証で、目的、仮説、実行結果、変更内容、Lineageの 100% が閲覧可能である。

## Out of Scope

- Evolution Stepの物理削除
- Evolution Stepのアーカイブ
- Lineageから任意のEvolution StepまたはRunを直接除外する操作
- 本製品からの学習処理の開始、停止、再実行
- Dataset内のデータ行単位の追加、変更、削除の特定
- 全stepのMetric履歴の保存および表示

## Assumptions

- 初期MVPの利用者は単一の開発チーム内の開発者であり、認証、権限管理、利用者間のアクセス制御は対象外とする。
- Evolution Stepの目的と仮説は、利用者が自由記述で入力する。
- 外部の学習コードは、accuracyを0以上1以下の比率としてMLflowへ記録する。
- 学習処理は本製品の外部で行い、外部の学習コードが実行結果をMLflowに記録する。本製品はMLflowからRun、実測条件、評価指標、データセット識別情報を取得する。初期MVPで連携する実験管理ツールはMLflowのみとする。
- 変更内容は、利用者が記録する変更の意図・予定・定性的説明である。実測条件は、MLflowから取得する実行済みRunの条件であり、両者を区別して表示する。
- 実測条件はMLflowから取得できるすべてを表示および比較の対象とする。評価指標は、同一Metric名・同一stepの重複を最新timestamp、さらに同一timestampなら最大値で一本化した後、最大accuracyへ最初に到達した最小stepに記録された値だけを表示し、別stepの値で補完しない。自動結果差分はaccuracyだけを対象とする。accuracy以外の評価指標の最大化・最小化の判定、最良値の自動選択、利用者による比較対象の選択、および全stepのMetric履歴の保存・表示は初期MVPに含めない。
- Run候補の取得時はMLflow上の現在のRun名と状態を表示する。RunをEvolution Stepへ紐付ける時はMLflow上の存在を確認し、Run Referenceを保存する。RUNNINGまたはSCHEDULEDならSnapshot未確定、FINISHED、FAILED、またはKILLEDならSnapshot確定として扱う。
- Run候補は一度に20件を取得する。次の候補群を示す値は利用者へ直接入力させず、フロントエンドが同じ検索条件とともに保持して使用する。総件数は初期MVPでは表示しない。
- Evolution Step詳細は保存済み情報を先に表示し、その後で紐付いたRunを自動同期する。Snapshot未確定のRunが終了状態ならSnapshotを確定し、実行中なら未確定のままとする。同期に失敗しても保存済み情報の閲覧を妨げない。
- 一度確定したRun SnapshotのParameters、最良accuracyと最良step、そのstepのMetrics、データセット識別情報、確定時の実行状態、実行日時、および未加工メタデータは更新しない。Run ReferenceのRun名、現在状態、実行日時、および最終同期日時だけを変更可能な表示用情報として扱う。
- 確定済みRunを再開して追加学習する代わりに、継続学習を別の改善工程として追跡したい場合は、元Runのモデルまたはチェックポイントを引き継いだ新しいRun IDを作成し、新しいEvolution Stepの実行結果として紐付ける。
- Dataset Inputは用途と名前で対応付け、digestとsource識別情報を比較する。対応候補が複数あり一意に対応付けられない場合、またはいずれかのRunにDataset Inputが一件も記録されていない場合は比較情報なしとする。`parent_only`と`result_only`は各Runに記録されたDataset Inputの有無を表し、Dataset内のデータ行が追加または削除されたことを意味しない。定性的なデータ変更の説明は、Evolution Stepの変更内容として記録する。
- 一つのEvolution Stepが持つ派生元Runは0件または1件、実行結果Runは0件または1件とする。一つのRunを実行結果として紐付けられるEvolution Stepは0件または1件とする。実行結果Runは学習中から手動で紐付けることができ、未設定のEvolution Stepも登録できる。
- 一つの結果Runは、複数の後続Evolution Stepから派生元として参照できるため、Lineageは枝分かれできる。
- Runの新規登録、変更、解除では、一つのRunを複数のEvolution Stepの実行結果として紐付けず、同じRunを同じEvolution Stepの派生元Runと実行結果Runの両方に指定せず、Lineageに循環を生じさせない。違反する操作は拒否し、理由を利用者に示す。
- 派生元Runと実行結果RunはEvolution Step登録後も変更または解除できる。Runの変更・解除はEvolution Stepの削除ではなくUpdateとして扱い、変更対象、変更前後のRun、変更日時を全履歴として保持する。変更後は現在の紐付けでLineageを再構成する。
- Runの変更・解除は対象のEvolution Stepだけに適用し、他のEvolution Stepの派生元Runまたは実行結果Runを自動変更しない。実行結果RunでなくなったRunは、必要に応じてLineage上の上流境界Runとして扱う。
- Evolution Stepの目的、仮説、変更内容はいつでも編集できる。各編集の対象項目、編集前と編集後の内容、編集日時を変更履歴として保持し、編集日時順に確認できる。
- 実測条件の差分は、条件名と値を比較して追加、変更、削除として扱う。accuracy差分は、実行結果Runの最良accuracyから派生元Runの最良accuracyを引いて算出する。
- Lineageは、選択したEvolution Stepを中心に、すべての祖先と子孫を直近の世代から外側へ広がる一覧として確認する範囲とし、グラフィカルな可視化は含めない。
- Decision、Reason、Next Actionの管理、全体状況を集約するDashboard、本番環境への自動配備、環境構築の自動化、高度な画面改善は初期MVPに含めない。
- MLflow Run状態を常時監視するバックグラウンド処理は初期MVPに含めない。Run状態の確認とSnapshot確定はEvolution Step詳細の表示を契機として行う。
