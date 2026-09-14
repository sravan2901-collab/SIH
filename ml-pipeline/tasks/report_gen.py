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


@celery_app.task(name="tasks.generate_report")
def generate_report(scan_id: str):
    """Report generation stub (Phase 3).

    Conceptually sets Scan.status="processing" and completes task chain.
    Real PDF/DOCX report generation lands in Phase 9.
    """
    logger.info("Setting Scan.status='processing' for scan_id=%s (stub)", scan_id)
    update_scan_status(scan_id, "processing")
    return scan_id

