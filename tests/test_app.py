import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np


class MontageApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.old_cwd = os.getcwd()
        os.chdir(cls.temporary_directory.name)
        os.environ["PHOTOMONTAGE_SKIP_SAMPLE_MATERIALS"] = "1"
        sys.modules.pop("app", None)
        cls.app_module = importlib.import_module("app")
        cls.app_module.app.config.update(TESTING=True)
        cls.client = cls.app_module.app.test_client()

        cls.material_dir = Path(cls.temporary_directory.name) / "materials"
        cls.material_dir.mkdir()
        material = np.full((12, 12, 3), (60, 120, 180), dtype=np.uint8)
        cv2.imwrite(str(cls.material_dir / "material.png"), material)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.old_cwd)
        os.environ.pop("PHOTOMONTAGE_SKIP_SAMPLE_MATERIALS", None)
        cls.temporary_directory.cleanup()

    @staticmethod
    def _target_upload():
        target = np.full((8, 10, 3), (60, 120, 180), dtype=np.uint8)
        success, encoded = cv2.imencode(".png", target)
        if not success:
            raise AssertionError("Unable to encode API test fixture")
        return io.BytesIO(encoded.tobytes())

    def test_upload_is_not_persisted_and_result_is_returned(self):
        response = self.client.post(
            "/api/montage",
            data={
                "image_file": (self._target_upload(), "target.png"),
                "element_dir": str(self.material_dir),
                "org_img_pixel": "4",
                "element_img_pixel": "6",
                "cal_color_method": "average",
                "max_output_edge": "10000",
                "max_output_megapixels": "100",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["grid"], {"columns": 3, "rows": 2})
        self.assertIn("timings_ms", payload)
        self.assertEqual(list(Path("target_img").iterdir()), [])
        self.assertEqual(len(list(Path("montage_img").glob("*.png"))), 1)

    def test_large_limit_requires_explicit_confirmation(self):
        response = self.client.post(
            "/api/montage",
            data={
                "image_file": (self._target_upload(), "target.png"),
                "element_dir": str(self.material_dir),
                "org_img_pixel": "4",
                "element_img_pixel": "6",
                "max_output_edge": "10001",
                "max_output_megapixels": "100",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("allow_large_output", response.get_json()["error"])

    def test_invalid_upload_does_not_scan_materials(self):
        for content in (b"", b"not an image"):
            with self.subTest(content=content), patch.object(
                self.app_module, "_ensure_element_index"
            ) as scan:
                response = self.client.post(
                    "/api/montage",
                    data={"image_file": (io.BytesIO(content), "broken.png")},
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
                scan.assert_not_called()

    def test_empty_scan_reports_failure_and_preserves_previous_index(self):
        empty_dir = Path(self.temporary_directory.name) / "empty"
        empty_dir.mkdir(exist_ok=True)
        index = self.app_module.get_element_data_file(str(empty_dir))
        index.write_text("previous index", encoding="utf-8")
        response = self.client.post(
            "/api/update_elements", data={"element_dir": str(empty_dir)}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(index.read_text(encoding="utf-8"), "previous index")


if __name__ == "__main__":
    unittest.main()
