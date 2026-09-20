#!/usr/bin/env python3
"""Preview-only Pi camera that saves a color/B&W pair on GPIO26 presses."""

from __future__ import annotations

import signal
import threading
import traceback
from datetime import datetime
from pathlib import Path

import cv2
from gpiozero import Button
from picamera2 import Picamera2

from st7735s import ST7735S, crop_preview


PICTURES_DIR = Path("/home/pi/Pictures")
SHUTTER_GPIO = 26
PREVIEW_SIZE = (320, 240)
STILL_SIZE = (2592, 1944)  # Native resolution of Pi Camera Module v1.3 (OV5647)
JPEG_QUALITY = 95


def image_paths(now: datetime) -> tuple[Path, Path]:
    """Return matching color and B&W paths with collision-resistant names."""
    stem = now.strftime("%Y%m%d_%H%M%S_%f")
    return (
        PICTURES_DIR / f"{stem}_color.jpg",
        PICTURES_DIR / f"{stem}_bw.jpg",
    )


def save_pair(frame_bgr, now: datetime | None = None) -> tuple[Path, Path]:
    """Save color first, then derive B&W from those same captured pixels."""
    color_path, bw_path = image_paths(now or datetime.now())
    options = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]

    if not cv2.imwrite(str(color_path), frame_bgr, options):
        raise OSError(f"could not write {color_path}")

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    if not cv2.imwrite(str(bw_path), gray, options):
        raise OSError(f"could not write {bw_path}")

    return color_path, bw_path


def run() -> None:
    PICTURES_DIR.mkdir(parents=True, exist_ok=True)

    stop_event = threading.Event()
    shoot_event = threading.Event()

    def stop(_signum=None, _frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    display = None
    camera = None
    shutter = None

    try:
        display = ST7735S()
        camera = Picamera2()

        preview_config = camera.create_preview_configuration(
            main={"size": PREVIEW_SIZE, "format": "RGB888"},
            display=None,
            buffer_count=3,
            controls={"FrameDurationLimits": (33_333, 100_000)},
        )
        still_config = camera.create_still_configuration(
            main={"size": STILL_SIZE, "format": "RGB888"},
            display=None,
            buffer_count=1,
        )

        camera.configure(preview_config)
        camera.start()

        # Active-low button: one press, one action. Camera work stays out of
        # gpiozero's callback thread.
        shutter = Button(SHUTTER_GPIO, pull_up=True, bounce_time=0.08)
        shutter.when_pressed = shoot_event.set

        print("Camera ready: preview active, shutter on GPIO26")

        while not stop_event.is_set():
            if shoot_event.is_set():
                shoot_event.clear()
                try:
                    # Picamera2 switches back to the preview configuration after
                    # returning this single full-resolution capture.
                    still = camera.switch_mode_and_capture_array(
                        still_config, "main"
                    )
                    color_path, bw_path = save_pair(still)
                    print(f"Saved {color_path.name} and {bw_path.name}")
                except Exception:
                    print("Capture failed")
                    traceback.print_exc()

            preview = camera.capture_array("main")
            display.show(crop_preview(preview))

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
