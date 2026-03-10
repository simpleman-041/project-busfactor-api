from datetime import datetime, timezone # timezoneは時差。
from typing import Any 

import httpx

from app.core.config import settings

class GitHubClient:
    """
    GitHub REST API 通信用クライアント。
    
    責務:
    - 共通ヘッダ付与
    - Github API 呼び出し
    - ページネーション処理
    - レート制限情報取得
    - repository / contributors / commits の取得
    """
    
    def __init__(self) -> None:
        self.base_url = settings.github_api_base_url.rstrip("/") # url結合時にスラッシュが重複することを防ぐ
        self.timeout = 20.0 # リクエストの待機時間。重い時に待ち続けてプログラムが落ちることを防ぐ。
    
    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json", # 通信はjson形式でお願い
            "X-GitHub-API-Version": "2022-11-28"     # APIの仕様を固定。
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}" # 鍵の提示を行う。
            
        return headers
    
    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}" # 通信先のアドレス完成
        
        with httpx.Client(timeout=self.timeout, headers=self._build_headers()) as client:
            response = client.request(method, url, params=params) # methodはHTTPメソッドを受け取るよ。GET,POSTとか。
        
        response.raise_for_status() # エラーがあったらプログラムを止める
        return response