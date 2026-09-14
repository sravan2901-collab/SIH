"""Unit tests for the core image preprocessing module (Phase 4).

Tests pure preprocessing logic using synthetically generated in-memory Pillow images:
- Deliberate 8-degree skew correction (assert output skew < 0.5 degrees).
- PDP rectangular region cropping (assert cropped=True).
- Non-rectangular or small contour handling (assert cropped=False without raising).
- DPI extraction round-trip (assert (150, 150) extracted correctly).
"""

from io import BytesIO
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

# Ensure ml-pipeline is on sys.path for direct import
repo_root = Path(__file__).resolve().parent.parent.parent
ml_pipeline_dir = repo_root / "ml-pipeline"
if str(ml_pipeline_dir) not in sys.path:
    sys.path.insert(0, str(ml_pipeline_dir))

from tasks.image_processing import _compute_skew_angle, preprocess_image  # noqa: E402


def test_deskew_reduces_skew_under_half_degree():
    """Generate an image with deliberate 8-degree skew, assert output skew is < 0.5 deg."""
    # Create white canvas with a high-contrast black rectangle
    canvas = Image.new("RGB", (600, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([150, 200, 450, 400], fill=(0, 0, 0))

    # Rotate by 8 degrees
    rotated = canvas.rotate(8.0, expand=False, fillcolor=(255, 255, 255))
    buf = BytesIO()
    rotated.save(buf, format="JPEG", dpi=(72, 72))
    raw_bytes = buf.getvalue()

    png_out, metadata = preprocess_image(raw_bytes)

    assert isinstance(png_out, bytes)
    assert len(png_out) > 0
    assert abs(metadata["skew_corrected_degrees"]) > 0.5

    # Measure remaining skew on the output image
    out_arr = cv2.imdecode(np.frombuffer(png_out, np.uint8), cv2.IMREAD_GRAYSCALE)
    edges = cv2.Canny(out_arr, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    assert contours, "Expected contours on preprocessed output"

    largest_c = max(contours, key=cv2.contourArea)
    rem_skew = _compute_skew_angle(largest_c)
    assert abs(rem_skew) < 0.5, f"Expected remaining skew < 0.5 deg, got {rem_skew}"


def test_pdp_crop_detects_and_crops_large_rectangular_region():
    """Generate an unskewed image with a prominent rectangular PDP (>40% area) and assert cropped=True."""
    # 500x500 total = 250,000 px^2; a 350x350 rectangle is 122,500 px^2 (49% of total)
    img = Image.new("RGB", (500, 500), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([75, 75, 425, 425], fill=(20, 20, 20))

    buf = BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    png_out, metadata = preprocess_image(raw_bytes)

    assert isinstance(png_out, bytes)
    assert metadata["cropped"] is True

    # Output dimensions should correspond to the cropped region
    cropped_arr = cv2.imdecode(np.frombuffer(png_out, np.uint8), cv2.IMREAD_GRAYSCALE)
    h, w = cropped_arr.shape[:2]
    assert 340 <= w <= 360
    assert 340 <= h <= 360


def test_pdp_crop_skips_when_no_large_rectangular_contour():
    """Generate an image with tiny shapes or uniform noise; assert cropped=False without raising."""
    # 500x500 image with only a tiny shape in the corner (20x20 = 400 px^2, 0.16% of area)
    noise_arr = np.random.randint(110, 140, (500, 500), dtype=np.uint8)
    img = Image.fromarray(noise_arr)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 30, 30], fill=0)

    buf = BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    png_out, metadata = preprocess_image(raw_bytes)

    assert isinstance(png_out, bytes)
    assert len(png_out) > 0
    assert metadata["cropped"] is False


def test_dpi_extraction_roundtrip():
    """Assert DPI extracted from a Pillow-saved image with explicit dpi=(150, 150) round-trips correctly."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="JPEG", dpi=(150, 150))
    raw_bytes = buf.getvalue()

    _, metadata = preprocess_image(raw_bytes)

    assert metadata["dpi"] == [150, 150]
