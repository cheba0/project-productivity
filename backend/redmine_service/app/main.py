from fastapi import FastAPI

from redmine_service.app.routers.integrations import router

app = FastAPI(title="Redmine Service")

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "redmine"}