# Bus Factor API 仕様書

## 1. プロジェクト概要

### 1.1 目的

GitHub リポジトリを対象に、開発知識の集中度を推定し、**Bus Factor** を算出する API を FastAPI で実装する。
本APIは学習用途とポートフォリオ用途を兼ね、以下の力を示すことを目的とする。

* FastAPI による API 設計・実装
* 外部 API（GitHub API）の利用
* レート制限・ページネーションへの対応
* DB を用いたキャッシュ設計
* Cloud Run へのデプロイ

### 1.2 背景

Bus Factor とは、主要開発者が何人離脱するとプロジェクト継続が困難になるかを示す指標である。
本プロジェクトでは研究レベルの厳密性よりも、**公開可能で説明可能な近似 Bus Factor API** の構築を優先する。

### 1.3 開発方針

* 最初から過剰に複雑化しない
* まずは **動く MVP** を完成させる
* その上で改良余地を残す
* API として壊れにくい設計を採用する

---

## 2. スコープ

### 2.1 本開発で実装する範囲（MVP）

* GitHub 公開リポジトリを対象とした Bus Factor 推定
* FastAPI による HTTP API 提供
* GitHub API からの contributors / commits 取得
* GitHub API のページネーション対応
* GitHub API の一次レート制限情報の取得
* DB キャッシュ機能
* Cloud Run デプロイ可能な構成
* Swagger UI (`/docs`) による確認

### 2.2 今回は実装しない範囲

* GitHub App 化
* 非同期ジョブキュー
* private repository 対応
* file 単位の厳密 ownership 推定
* PR / issue / review データを用いた知識推定
* 高度な依存関係解析
* 認証ユーザーごとの個別利用制御

---

## 3. 想定利用者

### 3.1 主対象

* OSS リポジトリの保守性を見たい開発者
* GitHub プロジェクトの知識集中リスクを見たい学習者
* 開発体制の偏りをざっくり把握したい人

### 3.2 利用シーン

* OSS 導入前の参考確認
* 個人開発 / チーム開発での知識集中確認
* 技術ポートフォリオとしてのデモ

---

## 4. システム構成

## 4.1 全体構成

```text
Client
  ↓
FastAPI (Cloud Run)
  ↓
Cache DB
  ↓
GitHub API
```

### 4.2 採用技術（予定）

* Python 3.12 系
* FastAPI
* Uvicorn
* SQLAlchemy
* SQLite（MVP）
* HTTP クライアント: httpx または requests
* Google Cloud Run

### 4.3 DB 方針

MVP では SQLite を採用する。
目的は永続化の重厚さよりも、以下の実現である。

* 解析結果のキャッシュ
* 同一 repo への無駄な GitHub API 再アクセス防止
* レスポンス速度改善

---

## 5. ドメイン知識整理

### 5.1 Bus Factor の定義

Bus Factor とは、主要開発者が何人離脱すると、プロジェクトの重要部分が一定割合以上失われるかを示す指標である。

### 5.2 今回の近似定義

本APIでは、MVP として次の近似を採用する。

* `knowledge ≈ commit contribution`
* contributors の commit 数から ownership を推定する
* ownership の大きい順に開発者を除外する
* 累積喪失率が `failure_threshold` に達した時点の人数を Bus Factor とする

### 5.3 failure_threshold の意味

`failure_threshold` は、プロジェクトがどの程度失われたら「崩壊」とみなすかを示す閾値である。

例:

* 0.5 = 重要度の 50% を失ったら崩壊
* 0.7 = より厳しく、70% 失ったら崩壊

MVP では **0.5** を初期値とする。

---

## 6. アルゴリズム仕様（MVP）

### 6.1 入力

* `owner`
* `repo`
* `window_days`（初期値: 180）
* `failure_threshold`（初期値: 0.5）

### 6.2 取得データ

GitHub API から以下を取得する。

1. リポジトリ情報
2. contributors 一覧
3. 指定期間内の commit 一覧

### 6.3 ownership の定義

各開発者の ownership は以下で求める。

```text
ownership = developer_contributions / total_contributions
```

### 6.4 Bus Factor 算出手順

1. contributors を contributions 降順で並べる
2. ownership を上から順に累積する
3. 累積 ownership が `failure_threshold` 以上になった時点の人数を Bus Factor とする

### 6.5 リスク分類

Bus Factor に応じてリスクを返す。

例:

* 1: high
* 2: medium
* 3以上: low

※ 閾値は今後調整可能とする。

### 6.6 制約

* 厳密な知識所有を示すものではない
* commit 数は理解度そのものではない
* review や issue 上の知識は反映しない

---

## 7. API 仕様

### 7.1 基本方針

MVP では **シンプル API + キャッシュ** を採用する。
ジョブ型 API ではなく、同期で結果を返す。

### 7.2 エンドポイント一覧

#### 7.2.1 ヘルスチェック

**GET** `/health`

レスポンス例:

```json
{
  "status": "ok"
}
```

#### 7.2.2 GitHub レート制限確認

**GET** `/rate-limit`

レスポンス例:

```json
{
  "limit": 5000,
  "remaining": 4920,
  "reset": 1710000000
}
```

#### 7.2.3 Bus Factor 解析

**GET** `/busfactor/{owner}/{repo}`

クエリパラメータ:

* `window_days`（任意、初期値 180）
* `failure_threshold`（任意、初期値 0.5）
* `refresh`（任意、初期値 false）

レスポンス例:

```json
{
  "repository": "owner/repo",
  "bus_factor": 2,
  "risk_level": "medium",
  "failure_threshold": 0.5,
  "window_days": 180,
  "contributors": [
    {"login": "alice", "contributions": 50, "ownership": 0.5},
    {"login": "bob", "contributions": 30, "ownership": 0.3},
    {"login": "carol", "contributions": 20, "ownership": 0.2}
  ],
  "cached": true
}
```

---

## 8. GitHub API 利用仕様

### 8.1 使用予定エンドポイント

* `GET /repos/{owner}/{repo}`
* `GET /repos/{owner}/{repo}/contributors`
* `GET /repos/{owner}/{repo}/commits`
* `GET /rate_limit`

### 8.2 レート制限対応

* 認証付きで GitHub API を利用する
* `X-RateLimit-Remaining` を監視する
* `X-RateLimit-Reset` を確認する
* 余裕が少ない場合は解析を制限する
* `Retry-After` がある場合はそれに従う

### 8.3 ページネーション対応

* `per_page=100` を使用する
* `Link` ヘッダーの `next` を辿る
* 指定上限に達したら打ち切る

### 8.4 分析範囲制限

MVP では以下を設ける。

* `window_days = 180` 初期値
* `max_pages` または `max_commits` による取得制限

---

## 9. キャッシュ仕様

### 9.1 目的

* GitHub API 呼び出し削減
* レスポンス高速化
* レート制限対策

### 9.2 基本動作

1. リクエスト受信
2. DB に対象 repo の解析結果があるか確認
3. 有効期限内であればキャッシュを返す
4. なければ GitHub API から再解析する

### 9.3 キャッシュ有効期限

MVP では仮に **24時間** とする。

### 9.4 強制再解析

`refresh=true` の場合はキャッシュを無視して再解析する。

---

## 10. DB 設計（MVP案）

### 10.1 テーブル: analyses

| カラム名              | 型        | 説明                  |
| ----------------- | -------- | ------------------- |
| id                | INTEGER  | 主キー                 |
| owner             | TEXT     | リポジトリ所有者            |
| repo              | TEXT     | リポジトリ名              |
| window_days       | INTEGER  | 分析期間                |
| failure_threshold | REAL     | 崩壊閾値                |
| bus_factor        | INTEGER  | 算出結果                |
| risk_level        | TEXT     | リスク分類               |
| contributors_json | TEXT     | contributors 情報JSON |
| created_at        | DATETIME | 作成日時                |
| expires_at        | DATETIME | キャッシュ期限             |

### 10.2 将来拡張

* github_rate_limit_logs
* analysis_history
* deep_analysis_results

---

## 11. エラー仕様

### 11.1 想定エラー

* GitHub リポジトリが存在しない
* GitHub API レート制限到達
* GitHub API 通信失敗
* 対象 repo が大きすぎる
* contributors が取得できない

### 11.2 代表レスポンス例

```json
{
  "detail": "GitHub API rate limit exceeded"
}
```

### 11.3 ステータスコード方針

* 200: 正常
* 400: 不正パラメータ
* 404: repo not found
* 429: rate limit exceeded
* 500: internal error
* 503: external API unavailable

---

## 12. 非機能要件

### 12.1 可用性

* 少人数アクセスで安定動作すること
* MVP では大規模アクセスは前提としない

### 12.2 保守性

* レイヤー分割を行う
* GitHub API 呼び出しは client 層へ分離する
* Bus Factor 算出処理は service 層へ分離する

### 12.3 可読性

* 型ヒントを付ける
* 関数責務を小さく分ける
* 設定値は定数 / settings にまとめる

---

## 13. ディレクトリ構成案

```text
app/
├── main.py
├── core/
│   ├── config.py
│   └── exceptions.py
├── routers/
│   ├── health.py
│   ├── rate_limit.py
│   └── busfactor.py
├── services/
│   └── busfactor_service.py
├── clients/
│   └── github_client.py
├── models/
│   └── analysis.py
├── schemas/
│   └── busfactor.py
├── db/
│   ├── database.py
│   └── crud.py
└── utils/
    └── datetime_helper.py
```

---

## 14. デプロイ方針

### 14.1 デプロイ先

Google Cloud Run

### 14.2 想定運用コスト

* Cloud Run: 無料枠中心
* SQLite: 追加費用なし
* GitHub API: 無料

### 14.3 デプロイ条件

* Docker 化する
* 環境変数で GitHub Token を管理する
* `/health` で稼働確認できるようにする

---

## 15. 今後の拡張案

### 15.1 v1.5

* 重み付き Bus Factor
* 重要領域（Hotspot）導入
* contributors の絞り込み

### 15.2 v2

* file / directory ownership
* DOA 風アルゴリズム
* PR / issue / review の反映
* 非同期ジョブ化
* GitHub App 対応

---

## 16. 開発優先順位

### Phase 1

* FastAPI 初期構築
* `/health` 実装
* GitHub client 実装
* `/rate-limit` 実装

### Phase 2

* contributors 取得
* Bus Factor 算出関数
* `/busfactor/{owner}/{repo}` 実装

### Phase 3

* DB キャッシュ
* エラーハンドリング
* Cloud Run デプロイ

### Phase 4

* テスト
* README 整備
* 今後の拡張整理

---

## 17. 現時点の決定事項まとめ

* API テーマは **Bus Factor API**
* 目的は **学習 + ポートフォリオ**
* GitHub 公開リポジトリを対象とする
* MVP は **シンプル API + キャッシュ**
* ownership は **commit contributions による近似**
* 初期 `failure_threshold` は **0.5**
* 初期 `window_days` は **180**
* DB は **SQLite**
* デプロイ先は **Cloud Run**

---

## 18. 未決定事項

* `max_commits` / `max_pages` の具体値
* キャッシュ期限の最終値
* リスク分類の閾値
* refresh 時の制限方針
* Deep Analysis を同一プロジェクト内で扱うか別バージョンに分けるか
