from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String,Text, UniqueConstraint # Unique..は一意制約、check..はカラム値制約。
from sqlalchemy.orm import Mapped, mapped_column # Mは型ヒント、mはカラムの詳細設定。

from app.db.database import Base

class AnalysisCache(Base):
    """
    BusFactor 分析結果のキャッシュを保存するテーブル
    """
    __tablename__ = "analysis_chache"
    
    __table_args__ = (
        # 複合一意制約！
        UniqueConstraint(
        "owner",
        "repo",
        "window_days",
        "failure_threshold",
        name="uq_analysis_cache_key", # nameは識別名。
    ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    owner: Mapped[str] = mapped_column(String, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False)

    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_threshold: Mapped[Float] = mapped_column(String, nullable=False)

    bus_factor: Mapped[int] = mapped_column(Integer, nullable=False)

    contributors_json: Mapped[str] = mapped_column(Text, nullable=False)
    total_contributions: Mapped[int] = mapped_column(Integer, nullable=False)

    analyzed_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class RefreshControl(Base):
    """
    refresh=trueによる強制再分析の最終実行時刻を保存するテーブル。15分制限を設けるため。
    """
    
    __tablename__ = "refresh_control"
    __table_args__ = (
        UniqueConstraint(
            "owner",
            "repo",
            name="uq_refresh_control_repo",
        ),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    owner: Mapped[str] = mapped_column(String, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False)
    
    last_refresh_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)