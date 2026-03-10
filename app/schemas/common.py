from pydantic import BaseModel, Field
# エンドポイントで呼びだして、ドキュメントに反映させよう。また、エラーを返すときに使う。
class HealthResponse(BaseModel): 
    """
    ヘルスチェック用のレスポンス
    """
    status: str = Field(..., examples=["ok"]) # ...は必須であることを、examplesはstatusに入る値のサンプル。今回は正常とわかる簡易的なものでよし。
    
class ErrorResponse(BaseModel):
    """
    共通のエラーレスポンス
    """
    detail: str = Field(..., examples=["Repository not found"])