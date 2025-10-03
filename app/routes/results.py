# app/routes/results.py
from fastapi import APIRouter, HTTPException, Query
from app.deps import db, gcs
import os, time
from functools import lru_cache

router = APIRouter()
RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]

# Small per-process cache for signed URLs (reduces GCS signing load for hot pages)
CACHE_TTL_SECONDS = 55

def _now_bucketed(ttl: int) -> int:
    # changes every <ttl> seconds; used to invalidate lru_cache entries
    return int(time.time() // ttl)

@lru_cache(maxsize=1024)
def _signed_url_cached(bucket: str, blob_path: str, exp_secs: int, salt: int) -> str:
    # salt ensures cache turns over every CACHE_TTL_SECONDS
    blob = gcs.bucket(bucket).blob(blob_path)
    return blob.generate_signed_url(version="v4", expiration=exp_secs, method="GET")

@router.get("/{job_id}/signed-urls")
def signed_urls(
    job_id: str,
    minutes: int = Query(60, ge=1, le=1440),
    prefix: str = Query("", description="Optional: only return files starting with this rel-path prefix, e.g. 'documents/'")
):
    """Return signed URLs for outputs of a completed job (optionally filtered by prefix)."""
    # Fetch ONLY the field we need (cheaper & faster)
    snap = db.collection("jobs").document(job_id).get(field_paths=["result_refs"])
    if not snap.exists:
        raise HTTPException(404, "job not found")

    data = snap.to_dict() or {}
    refs = data.get("result_refs") or {}   # { "documents/foo.csv": "gs://...", "images/roi_1.png": "gs://..." }

    exp_secs = minutes * 60
    out = {}
    salt = _now_bucketed(CACHE_TTL_SECONDS)  # churn cache roughly once a minute

    for rel in refs.keys():
        if prefix and not rel.startswith(prefix):
            continue
        blob_path = f"{job_id}/{rel}"  # we store everything under this key space
        out[rel] = _signed_url_cached(RESULTS_BUCKET, blob_path, exp_secs, salt)

    return {"jobId": job_id, "files": out}
