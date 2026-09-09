"""
backend/detection/merger.py
-----------------------------
Merges detections from Tier 1, Tier 2, and Tier 3 into a single unified
event stream with consistent category tagging.

Rules (applied in order):
  1. Tier-1 detections are kept as-is.
  2. Tier-2 detections that don't overlap Tier-1 boxes (IoU < threshold) are added.
  3. Tier-3 detections that don't overlap any Tier-1/2 box are added.
  4. Any remaining Tier-3 boxes that overlap a Tier-1/2 box are suppressed
     (the known-class detection takes precedence).

Category tagging:
  - Tier 1 confident result → use its category (Person / Vehicle / Animal / ...)
  - Tier 2 result → "Drone"
  - Tier 3 only → "Unidentified"

Phase: 3 (imported but not wired in Phase 1's pipeline.py to keep it simple)
"""

from __future__ import annotations

from typing import List, Tuple

from backend.ingestion.frame_model import Detection, SOURCE_TIER3

_IOU_SUPPRESSION_THRESHOLD = 0.3


def _iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    """Compute intersection-over-union of two (x1,y1,x2,y2) boxes."""
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])

    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter = inter_w * inter_h
    if inter == 0:
        return 0.0

    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def merge_detections(
    tier1: List[Detection],
    tier2: List[Detection],
    tier3: List[Detection],
    iou_threshold: float = _IOU_SUPPRESSION_THRESHOLD,
) -> List[Detection]:
    """
    Merge three detection lists into a single deduplicated stream.

    Returns a list of Detection objects with `suppressed=True` on any
    detection that was shadowed by a higher-tier detection.
    """
    result: List[Detection] = list(tier1)
    reference_boxes: List[Tuple[float, float, float, float]] = [d.bbox for d in tier1]

    # Add Tier-2 if they don't overlap Tier-1
    for det in tier2:
        overlaps = any(_iou(det.bbox, ref) >= iou_threshold for ref in reference_boxes)
        if not overlaps:
            result.append(det)
            reference_boxes.append(det.bbox)
        else:
            det.suppressed = True
            result.append(det)   # still in list but flagged, so visualiser can skip

    # Add Tier-3 if they don't overlap Tier-1 or Tier-2
    for det in tier3:
        overlaps = any(_iou(det.bbox, ref) >= iou_threshold for ref in reference_boxes)
        if not overlaps:
            result.append(det)
        else:
            det.suppressed = True
            result.append(det)

    return result
