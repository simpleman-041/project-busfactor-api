
---

# 1. `/health` のレスポンス

最小で十分です。

```json
{
  "status": "ok"
}
```

## Pydantic

```python
class HealthResponse(BaseModel):
    status: str
```

---

# 2. `/rate-limit` のレスポンス

GitHub API の現在状態を返します。

```json
{
  "limit": 5000,
  "remaining": 4920,
  "reset": 1710000000
}
```

## Pydantic

```python
class RateLimitResponse(BaseModel):
    limit: int
    remaining: int
    reset: int
```

---

# 3. `/busfactor/{owner}/{repo}` の成功レスポンス

これが主役です。
MVPならこのくらいがちょうど良いです。

```json
{
  "repository": "owner/repo",
  "bus_factor": 2,
  "risk_level": "medium",
  "failure_threshold": 0.5,
  "window_days": 180,
  "cached": true,
  "contributors": [
    {
      "login": "alice",
      "contributions": 50,
      "ownership": 0.5
    },
    {
      "login": "bob",
      "contributions": 30,
      "ownership": 0.3
    }
  ]
}
```

---

## Pydantic モデル案

```python
from pydantic import BaseModel
from typing import List


class ContributorOut(BaseModel):
    login: str
    contributions: int
    ownership: float


class BusFactorResponse(BaseModel):
    repository: str
    bus_factor: int
    risk_level: str
    failure_threshold: float
    window_days: int
    cached: bool
    contributors: List[ContributorOut]
```

---

# 4. エラーレスポンス

共通で1つ作ると扱いやすいです。

```json
{
  "detail": "Repository not found"
}
```

## Pydantic

```python
class ErrorResponse(BaseModel):
    detail: str
```

---

# 5. 想定する主要エラー

## 400

不正パラメータ

例:

```json
{
  "detail": "failure_threshold must be between 0 and 1"
}
```

---

## 404

repo が存在しない

例:

```json
{
  "detail": "Repository not found"
}
```

---

## 429

refresh 制限 or GitHub rate limit

例1:

```json
{
  "detail": "Refresh allowed once every 15 minutes"
}
```

例2:

```json
{
  "detail": "GitHub API rate limit exceeded"
}
```

---

## 503

GitHub API 障害

```json
{
  "detail": "GitHub API unavailable"
}
```

---

# 6. クエリパラメータの仕様

`GET /busfactor/{owner}/{repo}` に付けるのはこれです。

* `window_days: int = 180`
* `failure_threshold: float = 0.5`
* `refresh: bool = False`

FastAPI だとこう書けます。

```python
@router.get("/busfactor/{owner}/{repo}", response_model=BusFactorResponse)
def get_bus_factor(
    owner: str,
    repo: str,
    window_days: int = 180,
    failure_threshold: float = 0.5,
    refresh: bool = False
):
    ...
```

---

# 7. ここでのおすすめ

MVPでは **レスポンスは増やしすぎない** 方が良いです。
たとえば今はまだ入れなくていいもの：

* `analysis_id`
* `processing_time`
* `rate_limit_snapshot`
* `commit_count_used`

これらは後で追加できます。

---

# 8. いま確定して良い schema 一覧

```python
HealthResponse
RateLimitResponse
ContributorOut
BusFactorResponse
ErrorResponse
```

---
