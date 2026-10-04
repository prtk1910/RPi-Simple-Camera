from datetime import datetime
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from camera import draw_style_label, image_path, press_action
from film_styles import FILM_PROFILES


class CameraControlTests(unittest.TestCase):
    def test_press_duration_selects_one_action(self):
        self.assertEqual(press_action(0.2), "cycle")
        self.assertEqual(press_action(1.0), "cycle")
        self.assertEqual(press_action(1.01), "capture")

    def test_capture_name_contains_only_selected_style(self):
        path = image_path(datetime(2026, 10, 4, 12, 0, 0, 123456), 5)
        self.assertEqual(path.name, "20261004_120000_123456_ilford_bw.jpg")

    def test_every_style_preserves_preview_shape_and_is_announced(self):
        frame = np.full((135, 240, 3), (70, 120, 190), dtype=np.uint8)
        for name, style, _ in FILM_PROFILES:
            with self.subTest(name=name):
                preview = style(frame.copy(), preview=True)
                labelled = draw_style_label(preview, name)
                self.assertEqual(labelled.shape, frame.shape)
                self.assertFalse(np.array_equal(labelled, preview))


if __name__ == "__main__":
    unittest.main()
