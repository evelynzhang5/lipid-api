from fastapi import APIRouter, HTTPException, Query
from app.deps import db, gcs
import os

router = APIRouter()
RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]

@router.get("/{job_id}/signed-urls")
def signed_urls(job_id: str, minutes: int = Query(60, ge=1, le=1440)):
    """Return signed URLs for all outputs of a completed job."""
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(404, "job not found")

    d = snap.to_dict()
    refs = d.get("result_refs") or {}   # { "documents/foo.csv": "gs://...", "images/roi_1.png": "gs://..." }

    bucket = gcs.bucket(RESULTS_BUCKET)
    out = {}
    for rel, gs in refs.items():
        # All files live at gs://RESULTS_BUCKET/job_id/<rel>
        blob = bucket.blob(f"{job_id}/{rel}")
        url = blob.generate_signed_url(
            version="v4",
            expiration=minutes*60,
            method="GET"
        )
        out[rel] = url

    return {"jobId": job_id, "files": out}
