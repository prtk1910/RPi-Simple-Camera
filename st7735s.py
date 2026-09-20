"""Minimal direct-SPI driver for the Waveshare 0.96-inch ST7735S LCD."""

from __future__ import annotations

import time

import cv2
import numpy as np
import spidev
from gpiozero import OutputDevice


class ST7735S:
    """Drive a 160x80 ST7735S panel without X11, Wayland, or a framebuffer."""

    width = 160
    height = 80

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
        self._command(0x11)  # Sleep out
        time.sleep(0.12)
        self._command(0x21)  # Inversion on
        self._command(0xB1, bytes((0x05, 0x3A, 0x3A)))
        self._command(0xB2, bytes((0x05, 0x3A, 0x3A)))
        self._command(0xB3, bytes((0x05, 0x3A, 0x3A, 0x05, 0x3A, 0x3A)))
        self._command(0xB4, bytes((0x03,)))
        self._command(0xC0, bytes((0x62, 0x02, 0x04)))
        self._command(0xC1, bytes((0xC0,)))
        self._command(0xC2, bytes((0x0D, 0x00)))
        self._command(0xC3, bytes((0x8D, 0x6A)))
        self._command(0xC4, bytes((0x8D, 0xEE)))
        self._command(0xC5, bytes((0x0E,)))
        self._command(
            0xE0,
            bytes(
                (
                    0x10,
                    0x0E,
                    0x02,
                    0x03,
                    0x0E,
                    0x07,
                    0x02,
                    0x07,
                    0x0A,
                    0x12,
                    0x27,
                    0x37,
                    0x00,
                    0x0D,
                    0x0E,
                    0x10,
                )
            ),
        )
        self._command(
            0xE1,
            bytes(
                (
                    0x10,
                    0x0E,
                    0x03,
                    0x03,
                    0x0F,
                    0x06,
                    0x02,
                    0x08,
                    0x0A,
                    0x13,
                    0x26,
                    0x36,
                    0x00,
                    0x0D,
                    0x0E,
                    0x10,
                )
            ),
        )
        self._command(0x3A, bytes((0x05,)))  # 16-bit RGB565
        self._command(0x36, bytes((0xA8,)))  # Landscape orientation, BGR panel
        self._command(0x29)  # Display on
        time.sleep(0.02)

    def _set_full_window(self) -> None:
        # The 160x80 glass begins at controller column 1, row 26.
        self._command(0x2A, bytes((0x00, 0x01, 0x00, 0xA0)))
        self._command(0x2B, bytes((0x00, 0x1A, 0x00, 0x69)))
        self._command(0x2C)

    @staticmethod
    def bgr_to_rgb565(frame: np.ndarray) -> bytes:
        """Convert an exact 160x80 OpenCV BGR frame to big-endian RGB565."""
        if frame.shape != (ST7735S.height, ST7735S.width, 3):
            raise ValueError(
                f"expected an 80x160 BGR frame, received shape {frame.shape}"
            )
        b = frame[:, :, 0].astype(np.uint16)
        g = frame[:, :, 1].astype(np.uint16)
        r = frame[:, :, 2].astype(np.uint16)
        packed = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        return packed.astype(">u2", copy=False).tobytes()

    def show(self, frame: np.ndarray) -> None:
        self._set_full_window()
        self._dc.on()
        self._spi.writebytes2(self.bgr_to_rgb565(frame))

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
    """Center-crop any BGR camera frame to 2:1, then resize to 160x80."""
    height, width = frame.shape[:2]
    target_ratio = ST7735S.width / ST7735S.height
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
        frame, (ST7735S.width, ST7735S.height), interpolation=cv2.INTER_AREA
    )
