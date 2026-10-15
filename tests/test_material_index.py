import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from core.get_dir_data import GetDirImg
from core.montage_service import MontageOptions, generate_montage, load_element_index
from utils.img_tools import ImgTools
from utils.split_txt_data import SpiltTxtData


class MaterialIndexTests(unittest.TestCase):
    def test_semicolons_in_directory_and_filename_survive_scan_and_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            material = root / "素材;旅行" / "photo;01.png"
            pixels = np.full((8, 8, 3), (30, 60, 90), dtype=np.uint8)
            ImgTools.save_png(str(material), pixels)
            index = root / "index.txt"
            self.assertTrue(GetDirImg.get_specified_dir_img_data(material.parent, index))
            records = load_element_index(index)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].path, str(material))
            self.assertEqual(records[0].crop, (0, 0, 8, 8))
            output = root / "result.png"
            generate_montage(pixels, index, output, MontageOptions(4, 4))
            np.testing.assert_array_equal(ImgTools.pil_import_img_trans_cv2(str(output)), pixels)

    def test_legacy_parser_preserves_fields_and_rejects_incomplete_records(self):
        self.assertEqual(
            SpiltTxtData.split_img_resize_data("photo.png;(1, 2, 8, 8);(30, 60, 90);(90, 60, 30)\n"),
            ("photo.png", [1, 2, 8, 8], (30, 60, 90), (90, 60, 30)),
        )
        for record in ("photo.png;(0, 0, 8, 8)", "photo.png;(0, 0);(1, 2, 3);(1, 2, 3)",
                       "photo.png;(0, 0, 8, 8);(1, 2);(1, 2, 3)"):
            with self.subTest(record=record), self.assertRaises(ValueError):
                SpiltTxtData.split_img_resize_data(record)

    def test_rebuild_keeps_previous_index_readable_until_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            materials = root / "materials"
            materials.mkdir()
            ImgTools.save_png(str(materials / "photo.png"), np.zeros((8, 8, 3), dtype=np.uint8))
            index = root / "index.txt"
            index.write_text("previous index", encoding="utf-8")
            original_loader = ImgTools.pil_import_img_trans_cv2

            def load_while_reading_index(path):
                self.assertEqual(index.read_text(encoding="utf-8"), "previous index")
                return original_loader(path)

            with patch.object(ImgTools, "pil_import_img_trans_cv2", side_effect=load_while_reading_index):
                self.assertTrue(GetDirImg._write_index(materials, index))
            self.assertIn("photo.png;", index.read_text(encoding="utf-8"))
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_failed_replacement_preserves_index_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ImgTools.save_png(str(root / "photo.png"), np.zeros((8, 8, 3), dtype=np.uint8))
            index = root / "index.txt"
            index.write_text("previous index", encoding="utf-8")
            with patch("core.get_dir_data.os.replace", side_effect=OSError("disk error")):
                with self.assertRaisesRegex(OSError, "disk error"):
                    GetDirImg._write_index(root, index)
            self.assertEqual(index.read_text(encoding="utf-8"), "previous index")
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_invalid_materials_do_not_replace_previous_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.png").write_bytes(b"invalid")
            index = root / "index.txt"
            index.write_text("previous index", encoding="utf-8")
            self.assertFalse(GetDirImg._write_index(root, index))
            self.assertEqual(index.read_text(encoding="utf-8"), "previous index")
            self.assertEqual(list(root.glob("*.tmp")), [])
