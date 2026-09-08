import logging
import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "lmpc_minio_admin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "changeme_dev_only")

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
    config=Config(signature_version="s3v4"),
)

BUCKETS = ["raw-images", "preprocessed-images", "pdf-reports", "docx-reports"]


def ensure_buckets() -> None:
    for name in BUCKETS:
        try:
            s3_client.head_bucket(Bucket=name)
            logger.info("Bucket '%s' already exists.", name)
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket"):
                s3_client.create_bucket(Bucket=name)
                logger.info("Created bucket '%s'.", name)
            else:
                # Attempt creation if head_bucket failed due to missing bucket
                try:
                    s3_client.create_bucket(Bucket=name)
                    logger.info("Created bucket '%s'.", name)
                except Exception as create_err:
                    logger.warning("Could not ensure bucket '%s': %s", name, create_err)
