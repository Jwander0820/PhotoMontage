import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from core.get_dir_data import GetDirImg
from utils.img_tools import ImgTools


class MaterialIndexTests(unittest.TestCase):
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
