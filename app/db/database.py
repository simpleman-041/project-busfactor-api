from collections.abc import Generator # 型ヒント、インスタンスのチェックとしての役割がある。

from sqlalchemy import create_engine # DBとの物理的接続を管理する。「図書館」へ向かうための「道路」。
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker # D..はDBテーブルとPythonクラスを紐づける基盤。SはDBに対するCRUD操作。sはDBとの窓口。

from app.core.config import settings # 設定値を持つオブジェクト変数。

class Base(DeclarativeBase):
    pass

connect_args = {} # ドライバーに与える設定指示が入る。
if settings.database_url.startswith("sqlite"): # 将来的にDBを切り替える可能性があるから。
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False, # 自動同期の停止
    autocommit=False, # 自動確定の停止
    class_=Session # ここをのちに変更することでAsync対応、バリデーション、メソッド追加が出来る。
)

def init_db() -> None:
    from app.db import models
    
    Base.metadata.create_all(bind=engine) # base.metadataはモデル定義からの情報集合体。今はまだないけど、、、

def get_db() -> Generator[Session, None, None]: # リクエストが来たら仕事が終わるまで接続を開く。終わったら閉じる。
    db = SessionLocal()
    try: 
        yield db
    finally:
        db.close() 