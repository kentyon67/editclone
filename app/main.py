import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routers import billing, jobs, plugin, usage, videos

app = FastAPI(title="EditClone", version="0.4.0")

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


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.4.0"}
