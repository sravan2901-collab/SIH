"""Tasks re-export module for app and routers."""
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add ml-pipeline to sys.path across host and container mount paths
repo_dir = Path(__file__).resolve().parent.parent.parent
for candidate in (
    repo_dir / "ml-pipeline",
    Path("/app/ml-pipeline"),
    Path("/ml-pipeline"),
    Path(__file__).resolve().parent.parent / "ml_pipeline",
):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from tasks.preprocess import preprocess
    from tasks.ocr import run_ocr
    from tasks.classify import classify_fields
    from tasks.font_check import check_font
    from tasks.rule_validation import validate_rules
    from tasks.report_gen import generate_report
except ImportError:
    from app.celery_app import celery_app

    @celery_app.task(name="tasks.preprocess")
    def preprocess(scan_id: str):
        return scan_id

    @celery_app.task(name="tasks.run_ocr")
    def run_ocr(scan_id: str):
        return scan_id

    @celery_app.task(name="tasks.classify_fields")
    def classify_fields(scan_id: str):
        return scan_id

    @celery_app.task(name="tasks.check_font")
    def check_font(scan_id: str):
        return scan_id

    @celery_app.task(name="tasks.validate_rules")
    def validate_rules(scan_id: str):
        return scan_id

    @celery_app.task(name="tasks.generate_report")
    def generate_report(scan_id: str):
        return scan_id

__all__ = [
    "preprocess",
    "run_ocr",
    "classify_fields",
    "check_font",
    "validate_rules",
    "generate_report",
]
