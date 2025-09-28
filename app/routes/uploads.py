from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.deps import gcs, require_auth
import os, time

router = APIRouter()

UPLOADS_BUCKET = os.environ["UPLOADS_BUCKET"]

class SignedUploadIn(BaseModel):
    filename: str
    size: int
    mime: str

@router.post("/signed-upload")
def signed_upload(body: SignedUploadIn, _=Depends(require_auth)):
    if not body.filename.lower().endswith((".svs",".ndpi",".ome.tif",".tif",".tiff",".czi",".vsi",".mrxs")):
        raise HTTPException(400, "Unsupported suffix")
    bucket = gcs.bucket(UPLOADS_BUCKET)
    blob = bucket.blob(f"uploads/{int(time.time())}_{body.filename}")
    url = blob.generate_signed_url(version="v4", expiration=3600, method="PUT", content_type=body.mime)
    return {"signed_url": url, "gs_path": f"gs://{bucket.name}/{blob.name}"}
