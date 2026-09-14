import logging
import sys
from pathlib import Path

# Ensure backend and ml-pipeline are on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
for candidate in (backend_dir, Path("/app")):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.celery_app import celery_app  # noqa: E402
from app.storage import ensure_buckets, s3_client  # noqa: E402
from tasks.db import (  # noqa: E402
    get_scan_raw_image_path,
    update_scan_preprocessed,
    update_scan_status,
)
from tasks.image_processing import preprocess_image  # noqa: E402

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.preprocess")
def preprocess(self, scan_id: str):
    """Image Preprocessing Celery task (Phase 4).

    Downloads raw image from MinIO, performs deskewing, denoising, and PDP cropping,
    stores preprocessed PNG in MinIO, updates Scan database record, and passes metadata
    to the next link in the pipeline.
    """
    logger.info("Starting image preprocessing for scan_id=%s", scan_id)
    try:
        # a. Determine raw image path and download bytes from MinIO raw-images bucket
        raw_path = get_scan_raw_image_path(scan_id)
        if raw_path:
            raw_s3_key = raw_path.removeprefix("raw-images/").lstrip("/")
        else:
            raw_s3_key = f"{scan_id}/original.jpg"

        ensure_buckets()
        try:
            resp = s3_client.get_object(Bucket="raw-images", Key=raw_s3_key)
            raw_bytes = resp["Body"].read()
        except Exception:
            if not raw_path and raw_s3_key.endswith(".jpg"):
                raw_s3_key = f"{scan_id}/original.png"
                resp = s3_client.get_object(Bucket="raw-images", Key=raw_s3_key)
                raw_bytes = resp["Body"].read()
            else:
                raise

        # b. Call preprocess_image(raw_bytes)
        png_bytes, metadata = preprocess_image(raw_bytes)

        # c. Log warning if crop was skipped
        if not metadata.get("cropped", False):
            logger.warning(
                "PDP crop was skipped for scan_id=%s (no rectangular contour >= 40%% image area)",
                scan_id,
            )

        # d. Upload returned PNG bytes to MinIO preprocessed-images
        preprocessed_key = f"{scan_id}/preprocessed.png"
        preprocessed_path = f"preprocessed-images/{preprocessed_key}"
        s3_client.put_object(
            Bucket="preprocessed-images",
            Key=preprocessed_key,
            Body=png_bytes,
            ContentType="image/png",
        )
        logger.info("Uploaded preprocessed image to %s", preprocessed_path)

        # e. Update database with preprocessed_image_path and status="processing"
        update_scan_preprocessed(scan_id, preprocessed_path, status="processing")

        # f. Return dict for the next chain task
        return {
            "scan_id": scan_id,
            "preprocessed_key": preprocessed_path,
            "dpi": metadata.get("dpi", [72, 72]),
        }

    except Exception as exc:
        logger.error("Preprocess task failed for scan_id=%s: %s", scan_id, exc)
        try:
            update_scan_status(scan_id, "error")
        except Exception as db_exc:
            logger.error("Failed to update scan_id=%s status to error: %s", scan_id, db_exc)
        raise self.retry(exc=exc, max_retries=2, countdown=30)
