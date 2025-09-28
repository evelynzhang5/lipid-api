from fastapi import APIRouter, HTTPException
from app.deps import db

router = APIRouter()

@router.get("/config")
def viewer_config(imageId: str):
    snap = db.collection("images").document(imageId).get()
    if not snap.exists: raise HTTPException(404, "image not found")
    d = snap.to_dict()
    return {"dzi_base_uri": d["dzi_base_uri"], "overlays": d.get("overlay_refs", []), "legend": d.get("legend", {})}
