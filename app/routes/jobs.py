from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.deps import db, require_auth
import os

# NEW import: Cloud Run v2 Jobs client (supports overrides)
from google.cloud import run_v2

router = APIRouter()

PROJECT_ID      = os.environ["FIRESTORE_PROJECT"]
RUN_REGION      = os.environ["RUN_REGION"]
WORKER_JOB_NAME = os.environ["WORKER_JOB_NAME"]  # e.g. "lipid-worker-job"

class CreateJobIn(BaseModel):
    imageId: str
    mode: str            # "20X" | "40X"
    gs_input: str | None = None

@router.post("")
def create_job(body: CreateJobIn, _=Depends(require_auth)):
    # 1) create Firestore job doc
    doc = db.collection("jobs").document()
    job_id = doc.id
    doc.set({
        "status": "queued",
        "stage": "init",
        "pct": 0,
        "imageId": body.imageId,
        "mode": body.mode,
        "created_at": run_v2.datetime_pb2.Timestamp().GetCurrentTime()  # optional
    }, merge=True)

    # 2) build Cloud Run Jobs "run with overrides" request
    jobs_client = run_v2.JobsClient()
    job_name = f"projects/{PROJECT_ID}/locations/{RUN_REGION}/jobs/{WORKER_JOB_NAME}"

    # Per-execution env overrides for the container
    # (name is optional for single-container jobs)
    container_override = run_v2.RunJobRequest.Overrides.ContainerOverride(
        env=[
            run_v2.EnvVar(name="JOB_ID",   value=job_id),
            run_v2.EnvVar(name="MODE",     value=body.mode),
            run_v2.EnvVar(name="GS_INPUT", value=body.gs_input or "")
        ]
    )
    overrides = run_v2.RunJobRequest.Overrides(
        container_overrides=[container_override]
    )

    # 3) start the Job execution (async; returns long-running operation)
    op = jobs_client.run_job(
        request=run_v2.RunJobRequest(
            name=job_name,
            overrides=overrides,
        )
    )
    # Don’t block the API; the worker will update Firestore status as it runs.
    # If you prefer to wait until submission completes: op.result()

    return {"jobId": job_id}

@router.get("/{job_id}")
def get_job(job_id: str):
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(404, "job not found")
    return snap.to_dict()
