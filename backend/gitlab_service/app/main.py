from fastapi import FastAPI

from gitlab_service.app.routers.integrations import router

app = FastAPI(title="GitLab Service")

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "gitlab"}