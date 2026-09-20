import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from utils.img_tools import ImgTools


class ImageDecodingTests(unittest.TestCase):
    def test_upload_and_file_target_share_exif_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portrait.jpg"
            source = Image.new("RGB", (12, 8), (10, 30, 50))
            exif = Image.Exif()
            exif[274] = 6  # Rotate 90 degrees clockwise when displayed.
            source.save(path, exif=exif)
            target = ImgTools.pil_import_img_trans_cv2(path, apply_exif_orientation=True)
            uploaded = ImgTools.decode_image_bytes(path.read_bytes())
            self.assertEqual(target.shape, (12, 8, 3))
            np.testing.assert_array_equal(target, uploaded)
            # Material indices retain raw pixel coordinates from previous scans.
            self.assertEqual(ImgTools.pil_import_img_trans_cv2(path).shape, (8, 12, 3))

    def test_empty_or_corrupt_upload_is_a_validation_error(self):
        for content in (b"", b"not an image"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                ImgTools.decode_image_bytes(content)
