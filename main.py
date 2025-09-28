# lipid-workers/main.py
import os, sys, time, subprocess, shlex
from google.cloud import firestore, storage

PROJECT_ID = os.getenv("FIRESTORE_PROJECT")  # MUST be set in Job definition
REGION     = os.getenv("RUN_REGION", "us-west1")

JOB_ID  = os.getenv("JOB_ID")   # set via /jobs overrides
MODE    = os.getenv("MODE")     # "40X" or "20X"
GS_INPUT= os.getenv("GS_INPUT") # gs://bucket/path.czi | .vsi | .ome.tif

def die(msg, code=2):
    print(f"[ERROR] {msg}", flush=True)
    if PROJECT_ID and JOB_ID:
        try:
            db = firestore.Client(project=PROJECT_ID)
            db.document(f"jobs/{JOB_ID}").set({"status":"failed","error":msg}, merge=True)
        except Exception as e:
            print("Secondary Firestore error:", e, flush=True)
    sys.exit(code)

def set_progress(stage, pct, status="running", log=""):
    db = firestore.Client(project=PROJECT_ID)
    doc = db.document(f"jobs/{JOB_ID}")
    doc.set({
        "status": status,
        "stage": stage,
        "pct": pct,
        "log_tail": log,
        "updated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    print(f"[{JOB_ID}] {pct}% | {stage} | {log}", flush=True)

def gcs_download(gs_uri, local_path):
    # For really large WSIs you’ll stream/convert in place; for now, simple download
    bucket_name, blob_path = gs_uri.replace("gs://","").split("/",1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(local_path)

def upload_result(local_path, gs_uri):
    bucket_name, blob_path = gs_uri.replace("gs://","").split("/",1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_path}"

def run_qupath_headless(input_path, out_dir, args_dict=None):
    # Placeholder: invoke QuPath headless with your Groovy script & classifier
    # cmd = f"/opt/qupath/QuPath/bin/QuPath script --image '{input_path}' --script '/app/your.groovy' --args '...'"
    # subprocess.run(shlex.split(cmd), check=True)
    time.sleep(5)  # simulate

def run_cellpose_on_tiles(input_path, out_dir, args_dict=None):
    # Placeholder: invoke your Cellpose CLI / python for 20× path
    # e.g., subprocess.run(["python","/app/cellpose_infer.py","--input",input_path,"--out",out_dir], check=True)
    time.sleep(5)  # simulate

def main():
    if not (PROJECT_ID and JOB_ID and MODE and GS_INPUT):
        die("Missing required env: FIRESTORE_PROJECT, JOB_ID, MODE, GS_INPUT")

    set_progress("start", 0)

    # Stage 1: Ingest & (optional) convert to OME-TIFF for Viv
    set_progress("convert", 10, log="converting to OME-TIFF / probing WSI")
    local_in = f"/tmp/input{os.path.splitext(GS_INPUT)[1]}"
    gcs_download(GS_INPUT, local_in)
    # TODO: if input is .czi or .vsi, call bfconvert to make pyramidal OME-TIFF:
    # cmd = f"/opt/bftools/bfconvert -pyramid -compression LZW '{local_in}' /tmp/slide.ome.tiff"
    # subprocess.run(shlex.split(cmd), check=True)
    ome_path = "/tmp/slide.ome.tiff"
    # For now, pretend local_in is already OME-TIFF
    ome_path = local_in
    set_progress("convert", 25, log="OME-TIFF ready")

    # Stage 2: Analyze per MODE
    out_dir = "/tmp/out"
    os.makedirs(out_dir, exist_ok=True)
    if MODE.upper() == "40X":
        set_progress("analyze", 40, log="QuPath 40×")
        run_qupath_headless(ome_path, out_dir, args_dict={})
    elif MODE.upper() == "20X":
        set_progress("analyze", 40, log="Cellpose 20×")
        run_cellpose_on_tiles(ome_path, out_dir, args_dict={})
    else:
        die(f"Unknown MODE {MODE}")

    set_progress("analyze", 70, log="exporting overlays/masks/summary")

    # Stage 3: Export results to GCS (you define your paths/buckets)
    results_bucket = os.getenv("RESULTS_BUCKET")  # e.g., wsi-outputs
    if results_bucket:
        # Example: upload a dummy summary json
        import json
        summary_path = "/tmp/summary.json"
        with open(summary_path,"w") as f:
            json.dump({"job_id": JOB_ID, "mode": MODE, "ok": True}, f)
        res_gs = upload_result(summary_path, f"gs://{results_bucket}/{JOB_ID}/summary.json")
    else:
        res_gs = None

    set_progress("done", 100, status="succeeded", log="complete")
    # Also stamp finished_at
    firestore.Client(project=PROJECT_ID).document(f"jobs/{JOB_ID}") \
        .set({"finished_at": firestore.SERVER_TIMESTAMP, "result_summary": res_gs}, merge=True)

if __name__ == "__main__":
    main()
