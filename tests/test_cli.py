import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from utils.img_tools import ImgTools


class CommandLineTests(unittest.TestCase):
    def test_missing_custom_index_is_created_at_requested_path(self):
        entry_point = Path(__file__).resolve().parents[1] / "main.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ImgTools.save_png(
                str(root / "element_img" / "material.png"),
                np.full((8, 8, 3), 120, dtype=np.uint8),
            )
            ImgTools.save_png(str(root / "target.png"), np.full((4, 4, 3), 120, dtype=np.uint8))
            result = subprocess.run(
                [sys.executable, str(entry_point), "target.png", "--elements",
                 "custom/index.txt", "--sampling", "2", "--tile", "4", "--name", "測試"],
                cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((root / "custom" / "index.txt").is_file())
            self.assertTrue((root / "montage_img" / "Montage_測試.png").is_file())
