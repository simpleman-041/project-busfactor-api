# Bus Factor API 開発チェックリスト

## Phase A: 骨組みを作る

### 1. プロジェクト初期化

-   [✔] 仮想環境を作成する
-   [✔] FastAPI / Uvicorn / SQLAlchemy / Pydantic / httpx をインストール
-   [✔] `app/` ディレクトリを作成
-   [✔] フォルダ構成を作成
    -   [ ] core/
    -   [ ] routers/
    -   [ ] schemas/
    -   [ ] services/
    -   [ ] clients/
    -   [ ] db/
    -   [ ] utils/

### 2. 設定ファイル

-   [ ] `app/core/config.py`
-   [ ] GitHub Token を環境変数から取得
-   [ ] `MAX_COMMITS = 1000`
-   [ ] `CACHE_TTL_HOURS = 24`
-   [ ] `REFRESH_COOLDOWN_MINUTES = 15`
-   [ ] `DEFAULT_WINDOW_DAYS = 180`
-   [ ] `DEFAULT_FAILURE_THRESHOLD = 0.5`

### 3. DB接続

-   [ ] `app/db/database.py`
-   [ ] SQLAlchemy engine
-   [ ] SessionLocal
-   [ ] Base
-   [ ] テーブル初期化関数

### 4. DBモデル

-   [ ] `app/db/models.py`
-   [ ] AnalysisCache
-   [ ] RefreshControl
-   [ ] UNIQUE(owner, repo, window_days, failure_threshold)
-   [ ] UNIQUE(owner, repo)

### 5. Schema

-   [ ] ContributorOut
-   [ ] BusFactorResponse
-   [ ] RateLimitResponse
-   [ ] HealthResponse
-   [ ] ErrorResponse

### 6. 最小API

-   [ ] `/health` エンドポイント
-   [ ] FastAPI起動確認
-   [ ] `{ "status": "ok" }` を返す

------------------------------------------------------------------------

## Phase B: GitHub API

### 7. GitHub Client

-   [ ] 共通リクエスト関数
-   [ ] Authorization header
-   [ ] `/rate_limit` 取得
-   [ ] repo存在確認
-   [ ] contributors取得
-   [ ] commits取得
-   [ ] pagination対応
-   [ ] `per_page=100`
-   [ ] `max_commits=1000`

### 8. GitHub Clientテスト

-   [ ] rate_limit取得
-   [ ] contributors取得
-   [ ] commits取得
-   [ ] pagination確認

------------------------------------------------------------------------

## Phase C: DB操作

### 9. CRUD

-   [ ] キャッシュ検索
-   [ ] キャッシュ保存
-   [ ] refresh_control取得
-   [ ] refresh_control更新

### 10. DB確認

-   [ ] 保存できる
-   [ ] 取得できる
-   [ ] refresh更新

------------------------------------------------------------------------

## Phase D: Bus Factor計算

### 11. Service

-   [ ] ownership計算
-   [ ] BusFactor算出
-   [ ] risk_level判定
-   [ ] キャッシュ確認
-   [ ] refresh制御
-   [ ] GitHub API連携
-   [ ] DB保存

### 12. 動作確認

-   [ ] ownership計算確認
-   [ ] bus factor算出確認
-   [ ] risk分類確認
-   [ ] cache動作確認
-   [ ] refresh=true確認
-   [ ] refresh制限確認

------------------------------------------------------------------------

## Phase E: Router

### 13. `/rate-limit`

-   [ ] router作成
-   [ ] response確認

### 14. `/busfactor/{owner}/{repo}`

-   [ ] router作成
-   [ ] window_days
-   [ ] failure_threshold
-   [ ] refresh
-   [ ] response確認

### 15. router登録

-   [ ] health
-   [ ] rate_limit
-   [ ] busfactor
-   [ ] `/docs`確認

------------------------------------------------------------------------

## Phase F: デプロイ

### 16. Cloud Run準備

-   [ ] requirements.txt
-   [ ] Dockerfile
-   [ ] 起動コマンド
-   [ ] 環境変数設定
-   [ ] SQLiteの扱い

### 17. README

-   [ ] プロジェクト概要
-   [ ] Bus Factor説明
-   [ ] APIエンドポイント
-   [ ] ローカル起動方法
-   [ ] デプロイURL
-   [ ] 制約事項
