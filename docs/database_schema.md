# Bus Factor API - データベース設計（MVP）

## 1. 概要

このドキュメントでは **Bus Factor API MVP のデータベーススキーマ**を定義する。

データベースは主に次の2つの目的で使用される。

1. **分析結果をキャッシュ**して、不要な GitHub API 呼び出しを防ぐ
2. **refresh=true リクエストの制御**を行い、不正利用を防ぐ

この設計では、以下を重視している。

* シンプルさ
* 責務の明確な分離
* SQLite で簡単に実装できること
* 将来的な拡張のしやすさ

データベースは **2つのテーブル**で構成される。

* `analysis_cache`
* `refresh_control`

---

# 2. テーブル: analysis_cache

## 目的

Bus Factor 分析の **キャッシュ結果を保存する**テーブル。

このテーブルによって API は次のことが可能になる。

* キャッシュ結果を即座に返す
* GitHub API の利用回数を削減する
* レスポンス速度を向上させる
* 不要な再分析を防ぐ

---

## キャッシュキー

一意の分析結果は、次の組み合わせによって識別される。

```
(owner, repo, window_days, failure_threshold)
```

この組み合わせには **UNIQUE制約**が設定されている。

---

## カラム

| カラム                 | 型            | 説明                         |
| ------------------- | ------------ | -------------------------- |
| id                  | INTEGER (PK) | 主キー                        |
| owner               | TEXT         | GitHub リポジトリのオーナー          |
| repo                | TEXT         | GitHub リポジトリ名              |
| window_days         | INTEGER      | 分析対象の期間（日数）                |
| failure_threshold   | REAL         | Bus Factor 判定のしきい値         |
| bus_factor          | INTEGER      | 計算された Bus Factor           |
| contributors_json   | TEXT         | コントリビューター統計の JSON 配列       |
| total_contributions | INTEGER      | 集計された総コミット数                |
| analyzed_at         | DATETIME     | 分析が実行された時刻                 |
| expires_at          | DATETIME     | キャッシュの有効期限                 |

---

## レコード例

```json
{
  "owner": "torvalds",
  "repo": "linux",
  "window_days": 180,
  "failure_threshold": 0.5,
  "bus_factor": 2,
  "contributors_json": [
    {"login": "alice", "contributions": 50, "ownership": 0.5},
    {"login": "bob", "contributions": 30, "ownership": 0.3},
    {"login": "carol", "contributions": 20, "ownership": 0.2}
  ],
  "total_contributions": 100,
  "analyzed_at": "2026-03-07T10:00:00",
  "expires_at": "2026-03-08T10:00:00"
}
```

---

## SQL スキーマ

```sql
CREATE TABLE analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    failure_threshold REAL NOT NULL,
    bus_factor INTEGER NOT NULL,
    contributors_json TEXT NOT NULL,
    total_contributions INTEGER NOT NULL,
    analyzed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    UNIQUE(owner, repo, window_days, failure_threshold)
);
```

---

# 3. テーブル: refresh_control

## 目的

`refresh=true` パラメータの **悪用を防ぐ**。

このテーブルがない場合、ユーザーは何度も強制再分析を行えてしまい、以下の問題が発生する。

* GitHub API のレート制限の枯渇
* 不必要な外部 API 呼び出し
* DoS 的な挙動

このテーブルは **各リポジトリの最後の強制更新時刻**を保存する。

---

## Refresh ポリシー

API では次のルールを適用する。

* `refresh=true` は強制的に再分析を行う
* 各リポジトリは **15分に1回まで**しか refresh できない
* クールダウン中に refresh が行われた場合、API は次を返す

```
429 Too Many Requests
```

---

## カラム

| カラム             | 型            | 説明               |
| --------------- | ------------ | ---------------- |
| id              | INTEGER (PK) | 主キー              |
| owner           | TEXT         | GitHub リポジトリオーナー |
| repo            | TEXT         | GitHub リポジトリ名    |
| last_refresh_at | DATETIME     | 最後の強制更新時刻        |

---

## SQL スキーマ

```sql
CREATE TABLE refresh_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    last_refresh_at TEXT NOT NULL,
    UNIQUE(owner, repo)
);
```

---

# 4. データベースを用いたリクエスト処理フロー

## 通常リクエスト

```
GET /busfactor/{owner}/{repo}
```

処理手順

1. `analysis_cache` を検索
2. レコードが存在し、かつ `expires_at > now` の場合
3. キャッシュ結果を返す
4. それ以外の場合 GitHub 分析を実行
5. 結果を `analysis_cache` に保存

---

## Refresh リクエスト

```
GET /busfactor/{owner}/{repo}?refresh=true
```

処理手順

1. `refresh_control` を確認
2. `now - last_refresh_at < 15分` の場合
3. `429` を返す
4. それ以外は GitHub 分析を実行
5. `analysis_cache` を更新
6. `refresh_control.last_refresh_at` を更新

---

# 5. 設計判断

## なぜ contributors を JSON にしたのか

JSON を使用する理由

* シンプルに保存できる
* 柔軟な構造を持てる
* スキーマの複雑化を防ぐ
* MVP を高速に実装できる

必要であれば将来的に **別テーブルへ正規化**することも可能。

---

## なぜテーブルを2つに分けたのか

責務を分離することで設計が明確になる。

| テーブル            | 役割            |
| --------------- | ------------- |
| analysis_cache  | 分析結果の保存       |
| refresh_control | refresh レート制御 |

この分離により、システムの保守や拡張が容易になる。

---

# 6. 将来的な拡張

考えられる改善

### 追加テーブル

* `analysis_history`
* `github_rate_limit_log`
* `repository_metadata`

### 高度な Ownership モデル

Bus Factor の精度向上のために以下を追加できる。

* ファイル単位の ownership
* ディレクトリホットスポット分析
* PRレビュー参加
* issueディスカッション分析

これらの機能には追加テーブルが必要になる。

---

# 7. まとめ

最終的な MVP データベース構造

```
SQLite
 ├── analysis_cache
 └── refresh_control
```

主要パラメータ

* キャッシュTTL: **24時間**
* 最大分析コミット数: **1000**
* refresh クールダウン: **15分**
* リスクレベル: **3段階（high / medium / low）**

---
