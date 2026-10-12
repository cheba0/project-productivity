from fastapi import FastAPI
from analytics_service.app.routers.metrics import router as metrics_router

app = FastAPI(title="Analytics Service")

app.include_router(metrics_router)

@app.get("/health")
def health():
    return {"status": "ok"}
