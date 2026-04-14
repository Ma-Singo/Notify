from fastapi import FastAPI

from app.core.config import settings

app = FastAPI()


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
