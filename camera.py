#!/usr/bin/env python3
"""One-button Pi camera with a live film-style preview on a direct SPI display."""

from __future__ import annotations

import os
import signal
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import simplejpeg
from gpiozero import Button
from picamera2 import Picamera2

from film_styles import FILM_PROFILES, PROFILE_IDS, _WARM_YUV_STYLES, style_yuv_planes
from st7789 import ST7789, crop_preview


PICTURES_DIR = Path("/home/pi/Pictures")
SHUTTER_GPIO = 26
PREVIEW_SIZE = (320, 240)
JPEG_QUALITY = 92
LONG_PRESS_SECONDS = 1.0
STYLE_LABEL_SECONDS = 1.6


def press_action(duration: float) -> str:
    return "capture" if duration > LONG_PRESS_SECONDS else "cycle"


def image_path(now: datetime, style_index: int) -> Path:
    """Give every capture one timestamped filename with its selected style."""
    stem = now.strftime("%Y%m%d_%H%M%S_%f")
    return PICTURES_DIR / f"{stem}_{PROFILE_IDS[style_index]}.jpg"


def draw_style_label(frame: np.ndarray, name: str) -> np.ndarray:
    """Overlay a short, legible style announcement on the live viewfinder."""
    # Draw in screen coordinates; ST7789.show rotates the frame for the panel.
    labelled = cv2.rotate(frame, cv2.ROTATE_180)
    overlay = labelled[89:126]
    cv2.addWeighted(overlay, 0.35, overlay, 0, 0, dst=overlay)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.53
    (text_w, text_h), _ = cv2.getTextSize(name, font, scale, 1)
    cv2.putText(labelled, name, ((ST7789.width - text_w) // 2, 108 + text_h // 2),
                font, scale, (255, 255, 255), 1, cv2.LINE_AA)
    return cv2.rotate(labelled, cv2.ROTATE_180)


def publish_jpeg(pending_path: Path, photo_path: Path) -> None:
    """Publish a complete JPEG only after its data has reached storage."""
    with pending_path.open("rb") as saved:
        if saved.seek(0, os.SEEK_END) < 4:
            raise OSError("JPEG encoder produced an empty or incomplete image")
        saved.seek(0)
        start = saved.read(2)
        saved.seek(-2, os.SEEK_END)
        if start != b"\xff\xd8" or saved.read(2) != b"\xff\xd9":
            raise OSError("JPEG encoder produced an incomplete image")
        os.fsync(saved.fileno())
    pending_path.replace(photo_path)
    directory_fd = os.open(photo_path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def capture_selected(camera: Picamera2, preview_config, still_config,
                     style_index: int) -> tuple[Path, float]:
    """Free preview DMA buffers for the still, then restore preview promptly."""
    started = time.monotonic()
    photo_path = image_path(datetime.now(), style_index)
    pending_path = photo_path.with_name(f".{photo_path.stem}.part.jpg")
    request = None
    still = None
    preview_restored = False
    try:
        camera.stop()
        camera.configure(still_config)
        camera.start()
        if style_index == 0:
            request = camera.capture_request()
            request.save("main", str(pending_path))
            request.release()
            request = None
        else:
            arrays, _metadata = camera.capture_arrays(["main"])
            still = arrays[0]
            arrays = None
            camera.stop()
            camera.configure(preview_config)
            camera.start()
            preview_restored = True

            if style_index in _WARM_YUV_STYLES:
                y, u, v = style_yuv_planes(still, camera.sensor_resolution, style_index)
                encoded = simplejpeg.encode_jpeg_yuv_planes(
                    y, u, v, JPEG_QUALITY, fastdct=True)
            else:
                bgr = cv2.cvtColor(still, cv2.COLOR_YUV2BGR_I420)
                bgr = bgr[:camera.sensor_resolution[1], :camera.sensor_resolution[0]]
                still = None
                styled = FILM_PROFILES[style_index][1](bgr, preview=False)
                encoded = simplejpeg.encode_jpeg(
                    np.ascontiguousarray(styled), quality=JPEG_QUALITY,
                    colorspace="BGR", colorsubsampling="420", fastdct=True)
            pending_path.write_bytes(encoded)
        publish_jpeg(pending_path, photo_path)
    finally:
        pending_path.unlink(missing_ok=True)
        if request is not None:
            request.release()
        if not preview_restored:
            camera.stop()
            camera.configure(preview_config)
            camera.start()
    return photo_path, time.monotonic() - started


def run() -> None:
    PICTURES_DIR.mkdir(parents=True, exist_ok=True)
    stop_event = threading.Event()
    shoot_event = threading.Event()
    cycle_event = threading.Event()
    pressed_at = 0.0

    def stop(_signum=None, _frame=None) -> None:
        stop_event.set()

    def on_pressed() -> None:
        nonlocal pressed_at
        pressed_at = time.monotonic()

    def on_released() -> None:
        nonlocal pressed_at
        if not pressed_at:
            return
        duration = time.monotonic() - pressed_at
        pressed_at = 0.0
        (shoot_event if press_action(duration) == "capture" else cycle_event).set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    display = None
    camera = None
    shutter = None
    latest_preview = None
    style_index = 0
    label_until = 0.0

    try:
        display = ST7789()
        camera = Picamera2()
        preview_config = camera.create_preview_configuration(
            main={"size": PREVIEW_SIZE, "format": "RGB888"},
            raw=None, display=None, buffer_count=3, queue=False,
            controls={"FrameDurationLimits": (33_333, 100_000)},
        )
        still_config = camera.create_still_configuration(
            main={"size": camera.sensor_resolution, "format": "YUV420"},
            raw=None, buffer_count=1,
        )
        camera.configure(preview_config)
        camera.options["quality"] = JPEG_QUALITY
        camera.start()

        shutter = Button(SHUTTER_GPIO, pull_up=True, bounce_time=0.06)
        shutter.when_pressed = on_pressed
        shutter.when_released = on_released
        label_until = time.monotonic() + STYLE_LABEL_SECONDS
        print("Camera ready: tap GPIO26 for the next style; hold over 1s to capture",
              flush=True)

        while not stop_event.is_set():
            if cycle_event.is_set():
                cycle_event.clear()
                style_index = (style_index + 1) % len(FILM_PROFILES)
                label_until = time.monotonic() + STYLE_LABEL_SECONDS
                print(f"Selected {FILM_PROFILES[style_index][0]}", flush=True)

            if shoot_event.is_set():
                shoot_event.clear()
                try:
                    if latest_preview is not None:
                        display.capture_animation(latest_preview)
                    photo_path, seconds = capture_selected(
                        camera, preview_config, still_config, style_index)
                    print(f"Saved {photo_path.name} in {seconds:.2f}s", flush=True)
                except Exception:
                    print("Capture failed", flush=True)
                    traceback.print_exc()

            preview = camera.capture_array("main")
            viewfinder = crop_preview(preview)
            styled_preview = FILM_PROFILES[style_index][1](viewfinder, preview=True)
            if time.monotonic() < label_until:
                styled_preview = draw_style_label(styled_preview, FILM_PROFILES[style_index][0])
            latest_preview = styled_preview
            display.show(styled_preview)

    finally:
        if shutter is not None:
            shutter.close()
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass
            camera.close()
        if display is not None:
            display.close()


if __name__ == "__main__":
    run()
