from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from camera import capture_selected, publish_jpeg


class PhotoSaveTests(unittest.TestCase):
    def test_complete_jpeg_is_published(self):
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / '.pending.jpg'
            final = Path(directory) / 'photo.jpg'
            ok, encoded = cv2.imencode('.jpg', np.zeros((8, 8, 3), np.uint8))
            self.assertTrue(ok)
            pending.write_bytes(encoded.tobytes())

            publish_jpeg(pending, final)

            self.assertFalse(pending.exists())
            self.assertEqual(final.read_bytes(), encoded.tobytes())

    def test_empty_or_truncated_jpeg_cannot_replace_a_photo(self):
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / '.pending.jpg'
            final = Path(directory) / 'photo.jpg'
            final.write_bytes(b'existing photo')
            for data in (b'', b'\xff\xd8', b'\xff\xd8unfinished'):
                with self.subTest(data=data):
                    pending.write_bytes(data)
                    with self.assertRaises(OSError):
                        publish_jpeg(pending, final)
                    self.assertEqual(final.read_bytes(), b'existing photo')

    def test_failed_capture_removes_partial_file_and_restores_preview(self):
        for interrupted in (False, True):
            with self.subTest(interrupted=interrupted), tempfile.TemporaryDirectory() as directory:
                camera = Mock()
                request = camera.capture_request.return_value

                def failed_save(_stream, filename):
                    Path(filename).write_bytes(b'')
                    if interrupted:
                        raise OSError('simulated interrupted save')

                request.save.side_effect = failed_save
                with patch('camera.PICTURES_DIR', Path(directory)):
                    with self.assertRaises(OSError):
                        capture_selected(camera, 'preview', 'still', 0)

                self.assertEqual(list(Path(directory).iterdir()), [])
                request.release.assert_called_once()
                self.assertEqual(camera.configure.call_args.args, ('preview',))
                self.assertEqual(camera.start.call_count, 2)


if __name__ == '__main__':
    unittest.main()
