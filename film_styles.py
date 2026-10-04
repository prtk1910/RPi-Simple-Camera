"""Film styles shared with the Pi Zero film camera. OpenCV frames are BGR."""

from __future__ import annotations

import cv2
import numpy as np

PROFILE_W, PROFILE_H = 240, 135

def _lut_from_curve(pts):
    xs = np.array([p[0] for p in pts], dtype=np.float32)
    ys = np.array([p[1] for p in pts], dtype=np.float32)
    return np.clip(np.interp(np.arange(256), xs, ys), 0, 255).astype(np.uint8)

# --- Channel LUTs ---
_LUT_CC_B = _lut_from_curve([(0,25),(64,80),(128,132),(192,188),(255,242)])
_LUT_CC_G = _lut_from_curve([(0,18),(64,72),(128,126),(192,184),(255,238)])
_LUT_CC_R = _lut_from_curve([(0,20),(64,75),(128,128),(192,185),(255,240)])

_LUT_KP_B = _lut_from_curve([(0,12),(64,68),(128,118),(192,172),(255,220)])
_LUT_KP_G = _lut_from_curve([(0, 8),(64,74),(128,130),(192,192),(255,248)])
_LUT_KP_R = _lut_from_curve([(0,10),(64,80),(128,138),(192,200),(255,255)])

_LUT_FV_B = _lut_from_curve([(0,0),(64,66),(128,140),(192,208),(255,255)])
_LUT_FV_G = _lut_from_curve([(0,0),(64,62),(128,135),(192,205),(255,255)])
_LUT_FV_R = _lut_from_curve([(0,0),(64,60),(128,130),(192,200),(255,255)])

_LUT_FA_B = _lut_from_curve([(0,8),(64,70),(128,126),(192,188),(255,245)])
_LUT_FA_G = _lut_from_curve([(0,4),(64,70),(128,130),(192,194),(255,250)])
_LUT_FA_R = _lut_from_curve([(0,5),(64,72),(128,132),(192,196),(255,252)])

_LUT_IB   = _lut_from_curve([(0,0),(60,50),(128,128),(190,210),(255,255)])

_LUT_KG_B = _lut_from_curve([(0,20),(64,60),(128,110),(192,162),(255,210)])
_LUT_KG_G = _lut_from_curve([(0,10),(64,76),(128,132),(192,194),(255,248)])
_LUT_KG_R = _lut_from_curve([(0,15),(64,85),(128,142),(192,205),(255,255)])

# Small midtone shifts keep whites and skin from becoming orange.
_LUT_WN_B = _lut_from_curve([(0,0),(64,62),(128,124),(192,190),(255,255)])
_LUT_WN_G = _lut_from_curve([(0,0),(64,64),(128,128),(192,192),(255,255)])
_LUT_WN_R = _lut_from_curve([(0,0),(64,66),(128,132),(192,194),(255,255)])
_LUT_GD_B = _lut_from_curve([(0,0),(64,61),(128,123),(192,187),(255,255)])
_LUT_GD_G = _lut_from_curve([(0,0),(64,65),(128,129),(192,193),(255,255)])
_LUT_GD_R = _lut_from_curve([(0,0),(64,67),(128,134),(192,197),(255,255)])
_LUT_SN_B = _lut_from_curve([(0,6),(64,66),(128,124),(192,187),(255,249)])
_LUT_SN_G = _lut_from_curve([(0,6),(64,67),(128,128),(192,190),(255,250)])
_LUT_SN_R = _lut_from_curve([(0,7),(64,69),(128,133),(192,195),(255,252)])

def _make_channel_lut(lb, lg, lr):
    """Build the 3-channel LUT layout accepted by cv2.LUT."""
    return np.stack((lb, lg, lr), axis=1).reshape(256, 1, 3)

_LUT_CC = _make_channel_lut(_LUT_CC_B, _LUT_CC_G, _LUT_CC_R)
_LUT_KP = _make_channel_lut(_LUT_KP_B, _LUT_KP_G, _LUT_KP_R)
_LUT_FV = _make_channel_lut(_LUT_FV_B, _LUT_FV_G, _LUT_FV_R)
_LUT_FA = _make_channel_lut(_LUT_FA_B, _LUT_FA_G, _LUT_FA_R)
_LUT_KG = _make_channel_lut(_LUT_KG_B, _LUT_KG_G, _LUT_KG_R)
_LUT_WN = _make_channel_lut(_LUT_WN_B, _LUT_WN_G, _LUT_WN_R)
_LUT_GD = _make_channel_lut(_LUT_GD_B, _LUT_GD_G, _LUT_GD_R)
_LUT_SN = _make_channel_lut(_LUT_SN_B, _LUT_SN_G, _LUT_SN_R)

_LUT_SAT_072 = np.clip(np.arange(256) * 0.72, 0, 255).astype(np.uint8)
_LUT_SAT_085 = np.clip(np.arange(256) * 0.85, 0, 255).astype(np.uint8)
_LUT_SAT_090 = np.clip(np.arange(256) * 0.90, 0, 255).astype(np.uint8)
_LUT_SAT_095 = np.clip(np.arange(256) * 0.95, 0, 255).astype(np.uint8)
_LUT_SAT_145 = np.clip(np.arange(256) * 1.45, 0, 255).astype(np.uint8)
_LUT_HUE_MINUS_3 = ((np.arange(256, dtype=np.int16) - 3) % 180).astype(np.uint8)

# --- Vignette masks ---
def _make_vignette_mask(w, h, strength):
    Y, X     = np.ogrid[:h, :w]
    dist     = np.sqrt(((X - w/2)/(w/2))**2 + ((Y - h/2)/(h/2))**2)
    mask     = 1.0 - np.clip(dist * strength, 0, 1)
    mask_3ch = np.stack([mask, mask, mask], axis=-1)
    return (mask_3ch * 255).astype(np.uint8)

_VIG_MASK_PREVIEW_KP = _make_vignette_mask(PROFILE_W, PROFILE_H, 0.25)
_VIG_MASK_PREVIEW_KG = _make_vignette_mask(PROFILE_W, PROFILE_H, 0.30)

# --- Grain buffers (add/sub split avoids float32) ---
_noise_kg = np.random.normal(0, 4, (PROFILE_H, PROFILE_W, 3))
_GRAIN_KG_ADD = np.clip( _noise_kg, 0, 255).astype(np.uint8)
_GRAIN_KG_SUB = np.clip(-_noise_kg, 0, 255).astype(np.uint8)

_noise_ib = np.random.normal(0, 5, (PROFILE_H, PROFILE_W, 3))
_GRAIN_IB_ADD = np.clip( _noise_ib, 0, 255).astype(np.uint8)
_GRAIN_IB_SUB = np.clip(-_noise_ib, 0, 255).astype(np.uint8)
del _noise_kg, _noise_ib

# ============================================================
#  FAST HELPERS
# ============================================================

def _apply_channel_lut(img, lut):
    return cv2.LUT(img, lut)

def _sat_fast(img, scale):
    """Saturation via grayscale blend — avoids HSV round-trip."""
    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(img, scale, gray_3ch, 1.0 - scale, 0)

def _vignette_fast(img, mask_u8):
    h, w = img.shape[:2]
    mh, mw = mask_u8.shape[:2]
    # Clamp mask to actual image size (handles zoom crop size mismatches)
    m = mask_u8[:h, :w] if (h <= mh and w <= mw) else cv2.resize(mask_u8, (w, h), interpolation=cv2.INTER_NEAREST)
    return cv2.multiply(img, m, scale=1.0/255.0)

def _vignette_still(img, strength, rows_per_chunk=128):
    """Apply a vignette in-place without full-resolution float temporaries."""
    h, w = img.shape[:2]
    x_norm_sq = ((np.arange(w, dtype=np.float32) - w / 2) / (w / 2)) ** 2
    for y1 in range(0, h, rows_per_chunk):
        y2 = min(h, y1 + rows_per_chunk)
        y_norm_sq = ((np.arange(y1, y2, dtype=np.float32) - h / 2) / (h / 2)) ** 2
        dist = np.sqrt(y_norm_sq[:, np.newaxis] + x_norm_sq[np.newaxis, :])
        mask = ((1.0 - np.clip(dist * strength, 0, 1)) * 255).astype(np.uint8)
        mask_3ch = cv2.merge((mask, mask, mask))
        cv2.multiply(img[y1:y2], mask_3ch, dst=img[y1:y2], scale=1.0 / 255.0)
    return img

def _grain_fast(img, g_add, g_sub):
    h, w = img.shape[:2]
    gh, gw = g_add.shape[:2]
    if h != gh or w != gw:
        return img  # size guard during zoom
    return cv2.subtract(cv2.add(img, g_add), g_sub)

def _grain_still(img, amount, rows_per_chunk=128):
    """Generate signed grain in OpenCV, one bounded stripe at a time."""
    h, w = img.shape[:2]
    noise = np.empty((rows_per_chunk, w, 3), dtype=np.int16)
    for y1 in range(0, h, rows_per_chunk):
        y2 = min(h, y1 + rows_per_chunk)
        stripe = img[y1:y2]
        n = noise[:y2-y1]
        cv2.randn(n, (0, 0, 0), (amount, amount, amount))
        cv2.add(stripe, n, dst=stripe, dtype=cv2.CV_8U)
    return img

def _hsv_saturation(img, saturation_lut, hue_lut=None):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = cv2.LUT(hsv[:, :, 1], saturation_lut)
    if hue_lut is not None:
        hsv[:, :, 0] = cv2.LUT(hsv[:, :, 0], hue_lut)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

# ============================================================
#  FILM PROFILES
# ============================================================

def profile_standard(img, preview=True):
    return img

def profile_classic_chrome(img, preview=True):
    out = _apply_channel_lut(img, _LUT_CC)
    return _sat_fast(out, 0.72)

def profile_kodak_portra(img, preview=True):
    out = _apply_channel_lut(img, _LUT_KP)
    if preview:
        return _vignette_fast(_sat_fast(out, 0.85), _VIG_MASK_PREVIEW_KP)
    return _vignette_still(_sat_fast(out, 0.85), 0.25)

def profile_fuji_velvia(img, preview=True):
    out = _apply_channel_lut(img, _LUT_FV)
    return _hsv_saturation(out, _LUT_SAT_145, _LUT_HUE_MINUS_3)

def profile_fuji_astia(img, preview=True):
    out = _apply_channel_lut(img, _LUT_FA)
    return _sat_fast(out, 0.95)

def profile_ilford_bw(img, preview=True):
    pan = cv2.transform(img, np.array([[0.07, 0.72, 0.21]], dtype=np.float32))
    if pan.ndim == 3:
        pan = pan[:, :, 0]
    pan = cv2.LUT(pan, _LUT_IB)
    bgr = cv2.cvtColor(pan, cv2.COLOR_GRAY2BGR)
    if preview:
        return _grain_fast(bgr, _GRAIN_IB_ADD, _GRAIN_IB_SUB)
    return _grain_still(bgr, 5)

def profile_kodak_gold(img, preview=True):
    out = _apply_channel_lut(img, _LUT_KG)
    if preview:
        out = _sat_fast(out, 0.90)
        out = _vignette_fast(out, _VIG_MASK_PREVIEW_KG)
        return _grain_fast(out, _GRAIN_KG_ADD, _GRAIN_KG_SUB)
    out = _vignette_still(_sat_fast(out, 0.90), 0.30)
    return _grain_still(out, 4)

def profile_warm_natural(img, preview=True):
    return _apply_channel_lut(img, _LUT_WN)

def profile_golden_daylight(img, preview=True):
    return _apply_channel_lut(img, _LUT_GD)

def profile_soft_nostalgia(img, preview=True):
    return _sat_fast(_apply_channel_lut(img, _LUT_SN), 0.92)

FILM_PROFILES = [
    ("Standard",       profile_standard,       (180, 180, 180)),
    ("Classic Chrome", profile_classic_chrome,  ( 80, 180, 160)),
    ("Kodak Portra",   profile_kodak_portra,    ( 40, 140, 230)),
    ("Fuji Velvia",    profile_fuji_velvia,     ( 30, 200,  90)),
    ("Fuji Astia",     profile_fuji_astia,      (200, 160,  80)),
    ("Ilford B&W",     profile_ilford_bw,       (210, 210, 210)),
    ("Kodak Gold",     profile_kodak_gold,      (  0, 190, 230)),
    ("Warm Natural",   profile_warm_natural,    (100, 180, 230)),
    ("Golden Daylight",profile_golden_daylight, ( 60, 190, 240)),
    ("Soft Nostalgia", profile_soft_nostalgia,  (140, 170, 220)),
]
PROFILE_IDS = ["standard", "classic_chrome", "kodak_portra", "fuji_velvia",
               "fuji_astia", "ilford_bw", "kodak_gold", "warm_natural",
               "golden_daylight", "soft_nostalgia"]

def _chroma_lut(saturation=1.0, offset=0):
    values = (np.arange(256, dtype=np.float32) - 128) * saturation + 128 + offset
    return np.clip(values, 0, 255).astype(np.uint8)

# These restrained YUV adjustments approximate the warm RGB preview curves and
# let full-resolution warm photos use Picamera2's fast planar JPEG encoder.
_WARM_YUV_STYLES = {
    PROFILE_IDS.index("warm_natural"): (
        _lut_from_curve([(0,0),(64,64),(128,129),(192,193),(255,255)]),
        _chroma_lut(offset=-3), _chroma_lut(offset=2)),
    PROFILE_IDS.index("golden_daylight"): (
        _lut_from_curve([(0,0),(64,65),(128,130),(192,194),(255,255)]),
        _chroma_lut(offset=-4), _chroma_lut(offset=3)),
    PROFILE_IDS.index("soft_nostalgia"): (
        _lut_from_curve([(0,6),(64,67),(128,129),(192,191),(255,250)]),
        _chroma_lut(0.92, -3), _chroma_lut(0.92, 3)),
}

def style_yuv_planes(yuv, size, profile_idx):
    """Apply a warm style to YUV420 and return stride-aware planar views."""
    width, height = size
    y = yuv[:height, :width]
    planes = yuv.reshape((yuv.shape[0] * 2, yuv.strides[0] // 2))
    u = planes[2 * height: 2 * height + height // 2, :width // 2]
    v = planes[2 * height + height // 2:, :width // 2]
    y_lut, u_lut, v_lut = _WARM_YUV_STYLES[profile_idx]
    y[:] = cv2.LUT(y, y_lut)
    u[:] = cv2.LUT(u, u_lut)
    v[:] = cv2.LUT(v, v_lut)
    return y, u, v
