from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from st7789 import ST7789, crop_preview


class ImageHelperTests(unittest.TestCase):
    def test_crop_preview_fills_display_without_stretching(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:20] = 255

        preview = crop_preview(frame)

        self.assertEqual(preview.shape, (135, 240, 3))
        # A 4:3 source is center-cropped vertically, so the discarded top band
        # cannot appear in the 16:9 output.
        self.assertFalse(preview.any())

    def test_bgr_to_rgb565_primary_colors(self):
        frame = np.zeros((135, 240, 3), dtype=np.uint8)
        frame[0, 0] = (0, 0, 255)
        frame[0, 1] = (0, 255, 0)
        frame[0, 2] = (255, 0, 0)

        encoded = ST7789.bgr_to_rgb565(frame)

        self.assertEqual(
            encoded[:6], bytes((0xF8, 0x00, 0x07, 0xE0, 0x00, 0x1F))
        )


if __name__ == "__main__":
    unittest.main()
