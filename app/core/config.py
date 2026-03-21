from pydantic_settings import BaseSettings, SettingsConfigDict # クラスを定義するだけで環境変数や指定したファイルから値をマッピングする。Base..はデータの定義、Setting...はデータの読み方の制御

class Settings(BaseSettings):
    """
    アプリ全体の設定値を管理するクラス。
    環境変数があれば優先して、なければデフォルト値を使用する。
    """
    
    # Github API
    github_token: str | None = None # 認証用パスワードを入れる変数。
    github_api_base_url: str = "https://api.github.com" # リクエストの送り先となるURL。
    
    # Database
    database_url: str = "sqlite:///.bus_factor.db" # 今までやってきたように保存場所がローカルだが、接続文字列としてURLを書いている。拡張性が高く、何を使って開くかをプログラムへ伝えられるメリットがある。
    
    # Cache / analysis settings
    # 最大コミットが1000である理由はツールとしての軽量さ、分析精度のバランスをとっていると考えたから。
    cache_ttl_hours: int = 24
    max_commits: int = 1000
    refresh_cooldown_minutes: int = 15 
    
    # Default query parameter values 
    # 180日間ならエンジニアの休暇や短期タスクの影響を避けつつ、誰がコードを支えているかを判断できると考えた。
    # ブラックボックスの巨大化が危惧されるラインとしてプロジェクトの半数の知識が欠如すると危険と定義。
    default_window_days: int = 180
    default_failure_threshold: float = 0.5
    
    # .envファイルアクセス時の設定
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

# Settingオブジェクトを作り置きして、誰かが欲しい時にすぐに渡せるようにしている。
settings = Settings()
    