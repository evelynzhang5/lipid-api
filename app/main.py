from fastapi import FastAPI

from app.routes import jobs, uploads, viewer, results

app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(uploads.router, prefix="/auth", tags=["uploads"])
app.include_router(viewer.router, prefix="/viewer", tags=["viewer"])
app.include_router(results.router, prefix="/results", tags=["results"])   # NEW


@app.get("/health")
def health(): return {"ok": True}
