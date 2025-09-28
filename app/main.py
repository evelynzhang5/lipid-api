from fastapi import FastAPI
from app.routes import uploads, jobs, viewer

app = FastAPI(title="Lipid API")
app.include_router(uploads.router, prefix="/auth", tags=["uploads"])
app.include_router(jobs.router,    prefix="/jobs", tags=["jobs"])
app.include_router(viewer.router,  prefix="/viewer", tags=["viewer"])

@app.get("/health")
def health(): return {"ok": True}
