"""Minimal direct-SPI driver for a 1.14-inch 240x135 ST7789 IPS LCD."""

from __future__ import annotations

import time

import cv2
import numpy as np
import spidev
from gpiozero import OutputDevice


class ST7789:
    """Drive a 240x135 ST7789 panel without X11, Wayland, or a framebuffer."""

    width = 240
    height = 135

    def __init__(
        self,
        *,
        spi_bus: int = 0,
        spi_device: int = 0,
        dc_pin: int = 25,
        reset_pin: int = 27,
        backlight_pin: int = 18,
        speed_hz: int = 24_000_000,
    ) -> None:
        self._dc = OutputDevice(dc_pin, active_high=True, initial_value=False)
        self._reset = OutputDevice(reset_pin, active_high=True, initial_value=True)
        self._backlight = OutputDevice(
            backlight_pin, active_high=True, initial_value=False
        )

        self._spi = spidev.SpiDev()
        self._spi.open(spi_bus, spi_device)
        self._spi.mode = 0
        self._spi.max_speed_hz = speed_hz
        self._spi.no_cs = False

        self._initialise()
        self.clear()
        self._backlight.on()

    def _command(self, command: int, data: bytes = b"") -> None:
        self._dc.off()
        self._spi.writebytes([command])
        if data:
            self._dc.on()
            self._spi.writebytes(list(data))

    def _reset_panel(self) -> None:
        self._reset.on()
        time.sleep(0.05)
        self._reset.off()
        time.sleep(0.05)
        self._reset.on()
        time.sleep(0.12)

    def _initialise(self) -> None:
        self._reset_panel()
        self._command(0x36, bytes((0x70,)))  # Landscape orientation, RGB panel
        self._command(0x3A, bytes((0x05,)))  # 16-bit RGB565
        self._command(0xB2, bytes((0x0C, 0x0C, 0x00, 0x33, 0x33)))
        self._command(0xB7, bytes((0x35,)))
        self._command(0xBB, bytes((0x19,)))
        self._command(0xC0, bytes((0x2C,)))
        self._command(0xC2, bytes((0x01,)))
        self._command(0xC3, bytes((0x12,)))
        self._command(0xC4, bytes((0x20,)))
        self._command(0xC6, bytes((0x0F,)))
        self._command(0xD0, bytes((0xA4, 0xA1)))
        self._command(
            0xE0,
            bytes(
                (
                    0xD0,
                    0x04,
                    0x0D,
                    0x11,
                    0x13,
                    0x2B,
                    0x3F,
                    0x54,
                    0x4C,
                    0x18,
                    0x0D,
                    0x0B,
                    0x1F,
                    0x23,
                )
            ),
        )
        self._command(
            0xE1,
            bytes(
                (
                    0xD0,
                    0x04,
                    0x0C,
                    0x11,
                    0x13,
                    0x2C,
                    0x3F,
                    0x44,
                    0x51,
                    0x2F,
                    0x1F,
                    0x1F,
                    0x20,
                    0x23,
                )
            ),
        )
        self._command(0x21)  # Inversion on
        self._command(0x11)  # Sleep out
        time.sleep(0.12)
        self._command(0x29)  # Display on
        time.sleep(0.02)

    def _set_full_window(self) -> None:
        # The 240x135 glass begins at controller column 40, row 53.
        self._command(0x2A, bytes((0x00, 0x28, 0x01, 0x17)))
        self._command(0x2B, bytes((0x00, 0x35, 0x00, 0xBB)))
        self._command(0x2C)

    @staticmethod
    def bgr_to_rgb565(frame: np.ndarray) -> bytes:
        """Convert an exact 240x135 OpenCV BGR frame to big-endian RGB565."""
        if frame.shape != (ST7789.height, ST7789.width, 3):
            raise ValueError(
                f"expected a 135x240 BGR frame, received shape {frame.shape}"
            )
        b = frame[:, :, 0].astype(np.uint16)
        g = frame[:, :, 1].astype(np.uint16)
        r = frame[:, :, 2].astype(np.uint16)
        packed = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        return packed.astype(">u2", copy=False).tobytes()

    def show(self, frame: np.ndarray) -> None:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
        self._set_full_window()
        self._dc.on()
        self._spi.writebytes2(self.bgr_to_rgb565(frame))

    def capture_animation(self, frame: np.ndarray) -> None:
        """Show a brief shutter-frame contraction and flash over a preview."""
        for inset in (4, 18, 36):
            animated = frame.copy()
            cv2.rectangle(
                animated,
                (inset, inset),
                (self.width - inset - 1, self.height - inset - 1),
                (255, 255, 255),
                3,
            )
            self.show(animated)
            time.sleep(0.04)

        self.show(np.full_like(frame, 255))
        time.sleep(0.06)
        self.show(frame)

    def clear(self) -> None:
        self.show(np.zeros((self.height, self.width, 3), dtype=np.uint8))

    def close(self) -> None:
        try:
            self.clear()
            self._command(0x28)  # Display off
            self._backlight.off()
        finally:
            self._spi.close()
            self._dc.close()
            self._reset.close()
            self._backlight.close()


def crop_preview(frame: np.ndarray) -> np.ndarray:
    """Center-crop a BGR camera frame to 16:9, then resize to 240x135."""
    height, width = frame.shape[:2]
    target_ratio = ST7789.width / ST7789.height
    source_ratio = width / height

    if source_ratio > target_ratio:
        crop_width = int(round(height * target_ratio))
        left = (width - crop_width) // 2
        frame = frame[:, left : left + crop_width]
    elif source_ratio < target_ratio:
        crop_height = int(round(width / target_ratio))
        top = (height - crop_height) // 2
        frame = frame[top : top + crop_height, :]

    return cv2.resize(
        frame, (ST7789.width, ST7789.height), interpolation=cv2.INTER_AREA
    )
