from fastapi import FastAPI

from beelife.api.v1.routers import analysis, beedar, devices, weather

app = FastAPI(title="beelife")

app.include_router(analysis.router, prefix="/v1")
app.include_router(beedar.router, prefix="/v1")
app.include_router(devices.router, prefix="/v1")
app.include_router(weather.router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
