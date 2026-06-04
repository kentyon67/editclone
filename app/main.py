import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routers import videos
from app.routers import jobs
from app.routers import billing

app = FastAPI(title="EditClone", version="0.3.0")

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


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
