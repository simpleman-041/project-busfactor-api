from typing import Literal # 特定の具体的な値を扱いたいときに。今回は危険度を示す、low,medium,highの三段階！

from pydantic import BaseModel, Field

class ContributorOut(BaseModel): 
    """
    貢献者一人分の出力モデル
    """
    login: str = Field(..., examples=["steve"])
    contributions: float = Field(..., ge=0, examples=[30]) # 何件コミットしたか？ge,leは数値範囲制限。
    ownership: float = Field(..., ge=0.0, le=1.0, examples=[0.5]) # プロジェクトの何割の知識を有するか？

class BusFactorResponse(BaseModel):
    """
    BusFactor解析結果の出力モデル
    """
    # database_schema.mdファイルに各変数が持つ値が何を示すか書いてあるよ。
    repository: str = Field(..., examples=["owner/repo"])
    bus_factor: int = Field(..., ge=1, examples=[2])
    risk_level: Literal["high", "medium", "low"] = Field(..., examples=["medium"])
    failure_threshold: float = Field(..., ge=0.0, le=1.0, examples=[0.5])
    window_days: int = Field(..., ge=1, examples=[180])
    cached: bool = Field(..., examples=[True])
    contributors: list[ContributorOut] = Field(
        ...,
        examples=[
            [
                {"login": "steve", "contributions": 30, "ownership": 0.5},
                {"login": "dwayne", "contributions": 30, "ownership": 0.3},
            ]
        ],
    )

class RateLimitResponse(BaseModel):
    """
    GithubAPIレート制限確認用のレスポンス
    """
    
    limit: int = Field(..., ge=0, examples=[5000])
    remaining: int = Field(..., ge=0, examples=[4920])
    reset: int = Field(..., ge=0, examples=[1710000000])