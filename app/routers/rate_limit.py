from fastapi import APIRouter, HTTPException
import httpx

from app.clients.github_client import GitHubClient
from app.schemas.busfactor import RateLimitResponse

router = APIRouter(tags=["rate-limit"])

@router.get("/rate-limit", response_model=RateLimitResponse)
def get_rate_limit() -> RateLimitResponse:
    """
    GitHub API の現在の rate limit 情報を返す
    """
    client = GitHubClient()
    
    try:
        data = client.get_rate_limit()
        return RateLimitResponse(**data)
    
    except httpx.HTTPStatusError as exc: # 返事があるとき。
        status_code = exc.response.status_code
        
        if status_code == 403: # 03は閲覧権限なし、29はリクエストのレート制限。閲覧権限がないということはレート制限に引っかかったってこと。翻訳処理をしているj。
            raise HTTPException(
                status_code=429,
                detail="GitHub API rate limit exceed",
            ) from exc 
        
        raise HTTPException(
            status_code=503,
            detail="GitHub API unavailable",
        ) from exc
    
    except httpx.HTTPError as exc: # 返事がないとき。
        raise HTTPException(
            status_code=503,
            detail="GitHub API unavailable",
        ) from exc