import os
from fastapi import Header, HTTPException
from google.cloud import firestore, storage, tasks_v2

PROJECT_ID = os.environ["FIRESTORE_PROJECT"]

db = firestore.Client(project=PROJECT_ID)
gcs = storage.Client(project=PROJECT_ID)
tasks = tasks_v2.CloudTasksClient()

async def require_auth(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    return True

