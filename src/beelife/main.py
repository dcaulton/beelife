from fastapi import FastAPI

from beelife.api.v1.routers import beedar, weather

app = FastAPI(title="beelife")

app.include_router(beedar.router, prefix="/v1")
app.include_router(weather.router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
