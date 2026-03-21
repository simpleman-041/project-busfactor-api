今の仕様は、**シンプルAPI + キャッシュ**、GitHub API 連携、SQLite、Cloud Run 前提でした。
また、DBは `analysis_cache` と `refresh_control` の2テーブル構成で進める方針です 

---

# おすすめのフォルダ構成

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
├── schemas/
│   ├── common.py
│   └── busfactor.py
├── services/
│   └── busfactor_service.py
├── clients/
│   └── github_client.py
├── db/
│   ├── database.py
│   ├── models.py
│   └── crud.py
└── utils/
    └── datetime_helper.py
```

---

# 各フォルダの役割

## `main.py`

FastAPI アプリの起点です。

役割はかなり限定します。

* `FastAPI()` の生成
* router の登録
* 起動時処理の呼び出し

ここにロジックを書きすぎないのが大事です。

---

## `core/`

アプリ全体の共通設定を置く層です。

### `config.py`

* 環境変数の読み込み
* GitHub Token
* DBパス
* キャッシュTTL
* `MAX_COMMITS=1000`
* `REFRESH_COOLDOWN_MINUTES=15`

### `exceptions.py`

* 独自例外の定義
* `GitHubRateLimitExceededError`
* `RefreshCooldownError`
* `RepositoryNotFoundError`

ここを分けると、後でかなり見通しが良くなります。

---

## `routers/`

HTTPエンドポイント専用です。
**入力を受けて、service を呼んで、結果を返すだけ**にします。

### `health.py`

* `GET /health`

### `rate_limit.py`

* `GET /rate-limit`

### `busfactor.py`

* `GET /busfactor/{owner}/{repo}`

router には計算ロジックを書かないことが重要です。

---

## `schemas/`

Pydantic モデルを置きます。
APIの入出力定義です。

### `common.py`

* 汎用レスポンス
* エラーレスポンスなど

### `busfactor.py`

* `ContributorOut`
* `BusFactorResponse`
* `RateLimitResponse`

これを置くと、レスポンス形式が明確になります。

---

## `services/`

ここがアプリの中心です。
**業務ロジック**をまとめます。

### `busfactor_service.py`

役割は次の通りです。

* キャッシュ確認
* refresh 制御確認
* GitHub API 呼び出し
* ownership 計算
* Bus Factor 算出
* DB保存

つまり、Bus Factor API の本体です。

---

## `clients/`

外部API通信を隔離する層です。

### `github_client.py`

役割：

* GitHub API を叩く
* headers を付ける
* pagination 処理
* rate limit 情報を読む
* contributors / commits / repo 情報取得

GitHub APIの呼び出しが service に混ざると、一気に読みにくくなります。

---

## `db/`

DB専用です。

### `database.py`

* SQLAlchemy engine
* SessionLocal
* Base
* DB初期化

### `models.py`

* `AnalysisCache`
* `RefreshControl`

### `crud.py`

* キャッシュ検索
* キャッシュ保存
* refresh時刻取得/更新

DBアクセスを service から分離できます。

---

## `utils/`

小さな共通関数です。小物入れとしての感覚で扱うべきであり、詰め込みすぎない。

### `datetime_helper.py`

* 現在時刻取得
* expiry計算
* cooldown計算

---