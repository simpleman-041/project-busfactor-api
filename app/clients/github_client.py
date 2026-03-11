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
        path: str, # pathはエンドポイントのパス。
        params: dict[str, Any] | None = None, # paramsはURLクエリパラメータを指す。
    ) -> httpx.Response:
        url = f"{self.base_url}{path}" # 通信先のアドレス完成
        
        with httpx.Client(timeout=self.timeout, headers=self._build_headers()) as client:
            response = client.request(method, url, params=params) # response変数はリクエストによるサーバーの反応を受け取っている。methodはHTTPメソッドを受け取るよ。GET,POSTとか。
        
        response.raise_for_status() # エラーがあったらプログラムを止める
        return response
    
    def _get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 10,
    ) -> list[dict[str,Any]]:
        """
        ページネーション付きGETをまとめて取得。
        100件ずつ取得してmax_pagesまでたどる。
        """
        results: list[dict[str,Any]] = []
        base_params = params.copy() if params else {}
        base_params["per_page"] = 100
        
        for page in range(1, max_pages + 1):
            page_params = {**base_params, "page": page} # **は辞書展開。params引数も辞書だからね。
            # ここからはAPIを叩き、データをresultsとして結合していく。
            response = self._request("GET", path, params=page_params)
            data = response.json()
            
            if not isinstance(data, list):
                break
            
            results.extend(data)
            
            if len(data) < 100:
                break
        
        return results       
    
    def get_rate_limit(self) -> dict[str, int]:
        """
        GitHub APIのcore rate limit情報を返す。あとどれくらい使えるか？を示すため。
        """
        response = self._request("GET", "/rate_limit")
        payload = response.json()
        
        core = payload.get("ressources", {}).get("core",{}) # まずresourcesを探す。あるなら辞書を返す。これに対してcoreを探す。その値をcore変数に代入。という二段階の取り出し。
        return {
            "limit": int(core.get("limit", 0)),
            "remaining":  int(core.get("remaining",0)),
            "reset": int(core.get("reset"), 0)
        }
    
    def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        response = self._request("GET", f"/repos/{owner}/{repo}")
        return response.json
    
    def get_contributors(
        self,
        owner: str,
        repo: str,
        include_anonymous: bool = False, # 匿名ユーザーは結果に考慮しない。
        max_pages: int = 5,
    ) -> list[dict[str,Any]]:
        """
        contributors 一覧を取得する。
        commit数の降順で変える。
        """
        params: dict[str, Any] = {}
        if include_anonymous:
            params["anon"] = "true" # 匿名も加えるならクエリパラメータ付け加えるよ
        
        return self._get_paginated(
            f"repos/{owner}/{repo}/contributors",
            params=params,
            max_pages=max_pages,
        )
        
    def get_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | None = None,
        until: datetime | None = None,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """
        指定期間のcommit一覧を取得。
        """
        params: dict[str, Any] = {}
        
        if since is not None:
            params["since"] = self._to_iso8601_z(since) #　右辺は開始時間をISO 8601形式の文字列に変換しているよ。
        
        if until is not None:
            params["until"] = self._to_iso8601_z(until)
        
        return self._get_paginated(
            f"/repos/{owner}/{repo}/commits",
            params=params,
            max_pages=max_pages,
        )
        
    @staticmethod
    def _toi_iso_8601_z(dt: datetime) -> str:
        """
        GitHub API用にISO8601文字列へ変換する。
        """
        if dt.tzinfo is None: # tzinfoは世界のどこの時間か、時差の計算ルールを教えるためにある。TimeZoneInformationってことか。時差計算しないかするかの条件分岐。
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
            
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")