from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.deps import db, tasks, require_auth
import os, json
from google.cloud import tasks_v2

router = APIRouter()

PROJECT_ID   = os.environ["FIRESTORE_PROJECT"]
RUN_REGION   = os.environ["RUN_REGION"]
DISPATCH_URL = os.environ["DISPATCHER_URL"]

class CreateJobIn(BaseModel):
    imageId: str
    mode: str            # "20X" | "40X"
    gs_input: str | None = None

@router.post("")
def create_job(body: CreateJobIn, _=Depends(require_auth)):
    doc = db.collection("jobs").document()
    doc.set({"status":"queued","stage":"init","pct":0,"imageId":body.imageId,"mode":body.mode})
    queue = tasks.queue_path(PROJECT_ID, RUN_REGION, "lipid-queue")
    payload = {"job_id": doc.id, "mode": body.mode, "imageId": body.imageId, "gs_input": body.gs_input}
    task = {"http_request":{
        "http_method": tasks_v2.HttpMethod.POST, "url": DISPATCH_URL,
        "headers": {"Content-Type":"application/json"},
        "body": json.dumps(payload).encode()
    }}
    tasks.create_task(parent=queue, task=task)
    return {"jobId": doc.id}

@router.get("/{job_id}")
def get_job(job_id: str):
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists: raise HTTPException(404, "job not found")
    return snap.to_dict()
