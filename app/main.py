from fastapi import FastAPI

from app.routers import videos

app = FastAPI(title="EditClone", version="0.1.0")
app.include_router(videos.router)


@app.get("/health")
def health():
    return {"status": "ok"}
