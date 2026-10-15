import importlib.util
import hashlib
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np


class MontageApiTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        self.app_root = root / "application"
        self.app_root.mkdir()
        source = Path(__file__).resolve().parents[1]
        shutil.copy2(source / "app.py", self.app_root / "app.py")
        shutil.copytree(source / "templates", self.app_root / "templates")
        self.work_dir = root / "unrelated-cwd"
        self.work_dir.mkdir()
        old_cwd = os.getcwd()
        self.addCleanup(os.chdir, old_cwd)
        os.chdir(self.work_dir)
        environment = patch.dict(os.environ, {"PHOTOMONTAGE_SKIP_SAMPLE_MATERIALS": "1"})
        environment.start()
        self.addCleanup(environment.stop)
        name = "_photomontage_api_test"
        spec = importlib.util.spec_from_file_location(name, self.app_root / "app.py")
        self.app_module = importlib.util.module_from_spec(spec)
        sys.modules[name] = self.app_module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(self.app_module)
        self.app_module.app.config.update(TESTING=True)
        self.client = self.app_module.app.test_client()
        self.headers = {"X-PhotoMontage-Token": self.app_module.API_TOKEN}

        self.material_dir = self.app_root / "materials"
        self.material_dir.mkdir()
        material = np.full((12, 12, 3), (60, 120, 180), dtype=np.uint8)
        cv2.imwrite(str(self.material_dir / "material.png"), material)

    @staticmethod
    def _target_upload():
        target = np.full((8, 10, 3), (60, 120, 180), dtype=np.uint8)
        success, encoded = cv2.imencode(".png", target)
        if not success:
            raise AssertionError("Unable to encode API test fixture")
        return io.BytesIO(encoded.tobytes())

    def test_upload_and_download_work_from_an_unrelated_cwd(self):
        response = self.client.post(
            "/api/montage",
            headers=self.headers,
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
        self.assertEqual(list(self.app_module.TARGET_IMG_DIR.iterdir()), [])
        self.assertEqual(len(list(self.app_module.MONTAGE_IMG_DIR.glob("*.png"))), 1)
        with self.client.get(payload["result_url"]) as download:
            self.assertEqual(download.status_code, 200)
            rendered = cv2.imdecode(np.frombuffer(download.data, dtype=np.uint8), cv2.IMREAD_COLOR)
            self.assertEqual(rendered.shape, (12, 18, 3))
        self.assertEqual(list(self.work_dir.iterdir()), [])

    def test_large_limit_requires_explicit_confirmation(self):
        response = self.client.post(
            "/api/montage",
            headers=self.headers,
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
                    headers=self.headers,
                    data={"image_file": (io.BytesIO(content), "broken.png")},
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
                scan.assert_not_called()

    def test_empty_scan_reports_failure_and_preserves_previous_index(self):
        empty_dir = self.app_root / "empty"
        empty_dir.mkdir(exist_ok=True)
        index = self.app_module.get_element_data_file(str(empty_dir))
        index.write_text("previous index", encoding="utf-8")
        response = self.client.post(
            "/api/update_elements", headers=self.headers, data={"element_dir": str(empty_dir)}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(index.read_text(encoding="utf-8"), "previous index")

    def test_relative_scan_and_predefined_target_use_app_directory(self):
        response = self.client.post("/api/update_elements", headers=self.headers,
                                    data={"element_dir": "materials"})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["count"], 1)
        self.assertTrue(self.app_module.get_element_data_file(str(self.material_dir)).is_file())
        target = self.app_module.TARGET_IMG_DIR / "sample.png"
        target.write_bytes(self._target_upload().getvalue())
        with self.client.get("/target_img/sample.png") as preview:
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.data, target.read_bytes())
        response = self.client.post("/api/montage", headers=self.headers, data={
            "element_dir": "materials", "predefined_img": "sample.png",
            "org_img_pixel": "4", "element_img_pixel": "6",
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        with self.client.get(response.get_json()["result_url"]) as result:
            self.assertEqual(result.status_code, 200)
        self.assertEqual(list(self.work_dir.iterdir()), [])

    def test_legacy_relative_cache_is_not_reused_from_another_cwd(self):
        directory_hash = hashlib.md5(str(self.material_dir).encode("utf-8")).hexdigest()[:8]
        legacy_index = self.app_module.ELEMENT_DATA_DIR / f"cache_materials_{directory_hash}.txt"
        os.chdir(self.app_root)
        try:
            self.app_module.GetDirImg._write_index("materials", legacy_index)
        finally:
            os.chdir(self.work_dir)
        old_content = legacy_index.read_bytes()
        for misleading_material in (False, True):
            with self.subTest(misleading_material=misleading_material):
                if misleading_material:
                    (self.work_dir / "materials").mkdir()
                    cv2.imwrite(str(self.work_dir / "materials" / "material.png"),
                                np.zeros((12, 12, 3), dtype=np.uint8))
                response = self.client.post("/api/montage", headers=self.headers, data={
                    "image_file": (self._target_upload(), "target.png"), "element_dir": "materials",
                    "org_img_pixel": "4", "element_img_pixel": "6",
                })
                self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
                with self.client.get(response.get_json()["result_url"]) as result:
                    pixels = cv2.imdecode(np.frombuffer(result.data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    np.testing.assert_array_equal(pixels, np.full((12, 18, 3), (60, 120, 180), dtype=np.uint8))
        self.assertEqual(legacy_index.read_bytes(), old_content)

    def test_invalid_token_is_rejected_before_form_parsing(self):
        for endpoint in ("/api/update_elements", "/api/montage"):
            for token in (None, "wrong", "é", self.app_module.API_TOKEN + ",duplicate"):
                for content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
                    with self.subTest(endpoint=endpoint, token=token, content_type=content_type), patch(
                        "flask.wrappers.Request._load_form_data", side_effect=AssertionError("Parsed rejected body")
                    ):
                        response = self.client.post(endpoint, data={"element_dir": "materials"},
                            content_type=content_type,
                            headers={} if token is None else {"X-PhotoMontage-Token": token})
                        self.assertEqual(response.status_code, 403)
                        self.assertIn("重新整理", response.get_json()["error"])
        self.assertEqual(list(self.app_module.ELEMENT_DATA_DIR.iterdir()), [])
        self.assertEqual(list(self.app_module.MONTAGE_IMG_DIR.iterdir()), [])

    def test_token_in_form_query_or_cookie_does_not_authorize(self):
        token = self.app_module.API_TOKEN
        self.client.set_cookie("X-PhotoMontage-Token", token)
        for endpoint in ("/api/update_elements", "/api/montage"):
            response = self.client.post(endpoint + "?X-PhotoMontage-Token=" + token,
                data={"X-PhotoMontage-Token": token, "element_dir": "materials"})
            self.assertEqual(response.status_code, 403)

    def test_foreign_origin_is_rejected_even_with_valid_token(self):
        for endpoint in ("/api/update_elements", "/api/montage"):
            for origin in ("https://example.com", "null", "http://localhost.attacker.invalid", "http://localhost:5001"):
                with self.subTest(endpoint=endpoint, origin=origin), patch(
                    "flask.wrappers.Request._load_form_data", side_effect=AssertionError("Parsed rejected body")
                ):
                    response = self.client.post(endpoint, headers={**self.headers, "Origin": origin})
                    self.assertEqual(response.status_code, 403)

    def test_loopback_hosts_accept_same_origin_and_page_token_is_stable(self):
        for base_url in ("http://localhost", "http://127.0.0.1:5000", "http://[::1]:5000"):
            with self.subTest(base_url=base_url):
                page = self.client.get("/", base_url=base_url)
                self.assertEqual(page.status_code, 200)
                self.assertEqual(page.headers["Cache-Control"], "no-store")
                token = re.search(r'apiToken: "([^"]+)"', page.get_data(as_text=True)).group(1)
                self.assertEqual(token, self.app_module.API_TOKEN)
                response = self.client.post("/api/update_elements", base_url=base_url,
                    headers={"X-PhotoMontage-Token": token, "Origin": base_url},
                    data={"element_dir": "materials"})
                self.assertEqual(response.status_code, 200)

    def test_untrusted_hosts_cannot_read_token_or_use_api(self):
        for host in ("attacker.invalid", "localhost.attacker.invalid", "127.0.0.1.attacker.invalid"):
            with self.subTest(host=host):
                self.assertEqual(self.client.get("/", base_url=f"http://{host}").status_code, 400)
                self.assertEqual(self.client.post("/api/update_elements", base_url=f"http://{host}",
                    headers=self.headers, data={"element_dir": "materials"}).status_code, 400)

    def test_cross_origin_preflight_does_not_enable_cors(self):
        for endpoint in ("/api/update_elements", "/api/montage"):
            response = self.client.options(endpoint, headers={
                "Origin": "https://example.com", "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-PhotoMontage-Token",
            })
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)
            self.assertNotIn("Access-Control-Allow-Headers", response.headers)

    def test_old_token_fails_after_rotation_and_reloaded_page_recovers(self):
        with patch.object(self.app_module, "API_TOKEN", "new-process-token"):
            stale = self.client.post("/api/update_elements", headers=self.headers)
            self.assertEqual(stale.status_code, 403)
            page = self.client.get("/").get_data(as_text=True)
            token = re.search(r'apiToken: "([^"]+)"', page).group(1)
            response = self.client.post("/api/update_elements", headers={"X-PhotoMontage-Token": token},
                                        data={"element_dir": "materials"})
            self.assertEqual(response.status_code, 200)

    def test_blank_directory_does_not_scan_app_root(self):
        with patch.object(self.app_module.GetDirImg, "get_specified_dir_img_data") as scanner:
            for endpoint in ("/api/update_elements", "/api/montage"):
                response = self.client.post(endpoint, headers=self.headers, data={"element_dir": "  "})
                self.assertEqual(response.status_code, 400)
            scanner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
