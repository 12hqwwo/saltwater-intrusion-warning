"""Station anchors shared by the three-station spatial services."""
from bisect import bisect_right
import math

MY_THUAN_COORDINATE = [105.9263229, 10.27532005]
MY_THUAN_KM = 85.217605
MY_THUAN_RATIO = 0.68174084
THREE_STATION_MODE = 'PIECEWISE_3_STATION'
TWO_STATION_MODE = 'TWO_STATION_FALLBACK_MISSING_MYTHUAN'


def interpolate_anchors(chainage, anchors):
    """Continuous linear interpolation between adjacent along-river anchors."""
    if not math.isfinite(chainage) or len(anchors) < 2:
        raise ValueError('Invalid river interpolation input')
    if any(not math.isfinite(x) or not math.isfinite(ec) or ec < 0 for x, ec in anchors):
        raise ValueError('Invalid river station anchor')
    if any(a[0] >= b[0] for a, b in zip(anchors, anchors[1:])):
        raise ValueError('River anchors must be strictly increasing')
    index = max(0, min(len(anchors) - 2, bisect_right([a[0] for a in anchors], chainage) - 1))
    (start, left), (end, right) = anchors[index:index + 2]
    u = max(0, min(1, (chainage - start) / (end - start)))
    return left + (right - left) * u
