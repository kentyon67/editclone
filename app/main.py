import logging
import os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routers import billing, jobs, plugin, projects, style_profiles, usage, videos

logger = logging.getLogger(__name__)


def _reset_stale_jobs() -> None:
    """起動時に処理中のまま止まったジョブを失敗としてマークする。"""
    from app.services.storage import USE_CLOUD
    if not USE_CLOUD:
        return
    try:
        from app.services.storage import _client
        resp = (
            _client().table("jobs")
            .update({"status": "failed", "error_message": "サーバー再起動により中断されました"})
            .eq("status", "processing")
            .execute()
        )
        if resp.data:
            logger.info("起動時に %d 件のスタックジョブをリセットしました", len(resp.data))
    except Exception as e:
        logger.warning("スタックジョブのリセットに失敗: %s", e)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _reset_stale_jobs()
    yield


app = FastAPI(title="EditClone", version="0.9.0", lifespan=lifespan)

_origins_env = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(jobs.router)
app.include_router(billing.router)
app.include_router(usage.router)
app.include_router(plugin.router)
app.include_router(style_profiles.router)
app.include_router(projects.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.9.0"}
