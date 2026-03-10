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
        name="uq_analysis_cache_key",
    ),
        # カラム値制約！
        CheckConstraint(
            "risk_level IN ('high', 'medium', 'low')",
            name="ck_analysis_cache_lisk_level",
        ),
    )

id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

owner: Mapped[str] = mapped_column(String, nullable=False)
repo: Mapped[str] = mapped_column(String, nullable=False)

window_days: Mapped[int] = mapped_column(Integer, nullable=False)
failure_threshold: Mapped[Float] = mapped_column(String, nullable=False)

bus_factor: Mapped[int] = mapped_column(Integer, nullable=False)
risk_level: Mapped[str] = mapped_column(String, nullable=False)

cotributors_json: Mapped[str] = mapped_column(Text, nullable=False)
    