"""Core image preprocessing logic for LMPC Compliance System (Phase 4).

Provides pure, testable image processing functions:
- Deskew via Canny edge detection and minAreaRect contour analysis.
- Denoise via Non-Local Means (fastNlMeansDenoising).
- PDP (Principal Display Panel) perspective crop.
- DPI extraction via Pillow metadata.
"""

from io import BytesIO
from typing import Any

import cv2
import numpy as np
from PIL import Image


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 corner coordinates in clockwise order: [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _compute_skew_angle(contour: np.ndarray) -> float:
    """Compute skew angle in degrees relative to horizontal for a contour."""
    rect = cv2.minAreaRect(contour)
    (cx, cy), (w, h), angle = rect

    # In OpenCV 4.5+, angle is in [-90, 0)
    # If width < height, add 90 degrees to get the angle of the longer edge
    if w < h:
        angle = angle + 90.0

    # Normalize to (-45, 45] range
    if angle > 45.0:
        angle = angle - 90.0
    elif angle < -45.0:
        angle = angle + 90.0

    return float(angle)


def preprocess_image(raw_bytes: bytes) -> tuple[bytes, dict[str, Any]]:
    """Preprocess a raw image byte stream: decode, extract DPI, deskew, denoise, and PDP crop.

    Parameters:
        raw_bytes: Raw binary content of an uploaded image (JPEG or PNG).

    Returns:
        tuple containing:
            - png_bytes: Preprocessed image encoded as PNG bytes.
            - metadata: Dictionary containing:
                - "dpi": [dpi_x, dpi_y] extracted or default (72, 72)
                - "cropped": bool indicating whether PDP cropping was applied
                - "skew_corrected_degrees": float angle of rotation applied
    """
    # a. Decode raw bytes to numpy array (BGR)
    img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image from provided raw bytes")

    # b. Extract DPI via Pillow
    with Image.open(BytesIO(raw_bytes)) as pil_img:
        dpi_raw = pil_img.info.get("dpi", (72, 72))
    dpi = [int(round(dpi_raw[0])), int(round(dpi_raw[1]))]

    # c. Deskew: grayscale -> Canny -> minAreaRect on largest contour
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    skew_angle = 0.0
    if contours:
        largest_c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_c) > 0:
            skew_angle = _compute_skew_angle(largest_c)

    skew_corrected = 0.0
    h_img, w_img = gray.shape[:2]
    if abs(skew_angle) > 0.5:
        center = (w_img // 2, h_img // 2)
        m = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        gray = cv2.warpAffine(
            gray,
            m,
            (w_img, h_img),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        skew_corrected = round(skew_angle, 2)

    # d. Denoise via fastNlMeansDenoising
    denoised = cv2.fastNlMeansDenoising(
        gray,
        h=10,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    # e. PDP Crop: find largest rectangular contour; warpPerspective if >= 40% area
    total_area = denoised.shape[0] * denoised.shape[1]
    crop_edges = cv2.Canny(denoised, 50, 150)
    crop_contours, _ = cv2.findContours(
        crop_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    crop_contours = sorted(crop_contours, key=cv2.contourArea, reverse=True)

    cropped = False
    working_img = denoised

    found_box = None
    for c in crop_contours:
        peri = cv2.arcLength(c, True)
        for eps_factor in (0.02, 0.03, 0.04, 0.05):
            approx = cv2.approxPolyDP(c, eps_factor * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                area = cv2.contourArea(approx)
                if area >= 0.40 * total_area:
                    found_box = approx.reshape(4, 2).astype(np.float32)
                    break
        if found_box is not None:
            break

    if found_box is not None:
        ordered = _order_points(found_box)
        tl, tr, br, bl = ordered
        w_top = np.linalg.norm(tr - tl)
        w_bot = np.linalg.norm(br - bl)
        max_w = max(1, int(max(w_top, w_bot)))
        h_r = np.linalg.norm(tr - br)
        h_l = np.linalg.norm(tl - bl)
        max_h = max(1, int(max(h_r, h_l)))

        dst = np.array(
            [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
            dtype=np.float32,
        )
        transform_matrix = cv2.getPerspectiveTransform(ordered, dst)
        working_img = cv2.warpPerspective(working_img, transform_matrix, (max_w, max_h))
        cropped = True

    # f. Encode result as PNG
    success, encoded_buf = cv2.imencode(".png", working_img)
    if not success:
        raise RuntimeError("Failed to encode preprocessed image to PNG")

    # g. Return (png_bytes, metadata)
    metadata: dict[str, Any] = {
        "dpi": dpi,
        "cropped": cropped,
        "skew_corrected_degrees": skew_corrected,
    }
    return encoded_buf.tobytes(), metadata
