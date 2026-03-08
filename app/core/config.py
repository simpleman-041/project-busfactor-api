from pydantic_settings import BaseSettings, SettingConfigDict # クラスを定義するだけで環境変数や指定したファイルから値をマッピングする。Base..はデータの定義、Setting...はデータの読み方の制御

class Setting(BaseSettings):
    """
    アプリ全体の設定値を管理するクラス。
    環境変数があれば優先して、なければデフォルト値を使用する。
    """