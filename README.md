
---

# ✅ README（MVP完成版テンプレ）

そのまま貼れるレベルで書いています。あなたの仕様に完全準拠しています。

---

# Bus Factor API

GitHub リポジトリの開発知識の集中度を推定し、**Bus Factor（属人化リスク）**を算出する API です。

---

## 🚀 概要

Bus Factor とは、

> 「何人の主要開発者が離脱するとプロジェクトが崩壊するか」

を示す指標です。

本APIでは、GitHub のコミット情報を元に Bus Factor を近似的に算出します。

---

## 🎯 目的

* FastAPI を用いた API 設計・実装力の証明
* 外部 API（GitHub API）連携の実装
* キャッシュ設計（DB）の実装
* ポートフォリオとして公開可能なプロダクト作成 

---

## 🧠 アルゴリズム

Bus Factor は以下の手順で算出されます：

1. contributors を取得
2. commit 数から ownership を計算
3. 貢献度の高い順に並べる
4. 累積 ownership が threshold に達するまで人数を数える

```text
ownership = contributions / total_contributions
```

* デフォルト threshold: `0.5`
* window: `180日`

※ 厳密な知識量ではなく、commit ベースの近似です 

---

## 🏗️ システム構成

```
Client
  ↓
FastAPI
  ↓
SQLite（キャッシュ）
  ↓
GitHub API
```

* FastAPI
* SQLAlchemy
* SQLite（MVP）
* Cloud Run（デプロイ想定） 

---

## 📦 API エンドポイント

### 🔹 Health Check

```
GET /health
```

```json
{
  "status": "ok"
}
```

---

### 🔹 Rate Limit

```
GET /rate-limit
```

```json
{
  "limit": 5000,
  "remaining": 4920,
  "reset": 1710000000
}
```

---

### 🔹 Bus Factor 解析（メイン）

```
GET /busfactor/{owner}/{repo}
```

#### クエリ

| パラメータ             | 説明      | デフォルト |
| ----------------- | ------- | ----- |
| window_days       | 分析期間    | 180   |
| failure_threshold | 崩壊閾値    | 0.5   |
| refresh           | キャッシュ無視 | false |

---

#### レスポンス例

```json
{
  "repository": "owner/repo",
  "bus_factor": 2,
  "risk_level": "medium",
  "failure_threshold": 0.5,
  "window_days": 180,
  "cached": true,
  "contributors": [
    {
      "login": "alice",
      "contributions": 50,
      "ownership": 0.5
    }
  ]
}
```



---

## ⚡ キャッシュ仕様

* SQLite に結果を保存
* TTL: **24時間**
* 同一条件は再計算しない

```text
(owner, repo, window_days, failure_threshold)
```

で一意管理 

---

### 🔄 refresh パラメータ

```
?refresh=true
```

* 強制再解析
* 15分に1回まで（レート制御あり） 

---

## 🧱 ディレクトリ構成

```text
app/
├── main.py
├── core/
├── routers/
├── services/
├── clients/
├── schemas/
├── db/
└── utils/
```

* router：HTTP処理
* service：ビジネスロジック
* client：GitHub API
* db：キャッシュ管理 

---

## ⚠️ 制約

* commit 数ベースの近似
* PR / issue / review は未考慮
* private repo 非対応
* 大規模 repo は制限あり 

---

## 🔧 今後の拡張

* file単位 ownership
* PR / issue 分析
* 非同期ジョブ化
* GitHub App 対応 

---

## 🧪 動作確認

```bash
uvicorn app.main:app --reload
```

Swagger:

```
http://127.0.0.1:8000/docs
```

---
