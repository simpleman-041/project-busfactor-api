from fastapi import FastAPI

from app.db.database import init_db
from app.routers import busfactor, health, rate_limit

app = FastAPI(
    title="Bus Factor API",
    version="0.1.0",
    description="Estimate repository knowledge concentration from GitHub contributions.", # リポジトリ内の知識の偏りを割り出すよ！って意味。
)

@app.on_event("startup") #起動時の初期化処理
def on_startup() -> None:
    init_db()
    
app.include_router(health.router) # ここに集え、ルートたちよ！
app.include_router(rate_limit.router)
app.include_router(busfactor.router)