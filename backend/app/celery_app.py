import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("lmpc", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Register pipeline tasks
try:
    from app.tasks import (  # noqa: F401
        preprocess,
        run_ocr,
        classify_fields,
        check_font,
        validate_rules,
        generate_report,
    )
except Exception:
    pass

