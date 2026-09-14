import logging
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
for candidate in (backend_dir, Path("/app")):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.celery_app import celery_app  # noqa: E402
from tasks.db import update_scan_status  # noqa: E402

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_ocr")
def run_ocr(scan_id: str):
    """OCR processing stub (Phase 3).

    Conceptually sets Scan.status="processing" and passes scan_id through to next link in chain.
    Real PaddleOCR/Tesseract logic lands in Phase 5.
    """
    logger.info("Setting Scan.status='processing' for scan_id=%s (stub)", scan_id)
    update_scan_status(scan_id, "processing")
    return scan_id

