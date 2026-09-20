import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from core.montage_service import (
    ElementRecord,
    MontageOptions,
    calculate_tile_colors,
    generate_montage,
    match_elements,
    plan_output_size,
)
from utils.img_tools import ImgTools


class OutputPlanningTests(unittest.TestCase):
    def test_exact_default_limit_is_allowed(self):
        plan = plan_output_size(100, 100, MontageOptions(1, 100))
        self.assertEqual((plan.output_width, plan.output_height), (10_000, 10_000))
        self.assertFalse(plan.was_limited)

    def test_edge_and_pixel_budget_reduce_tile_size(self):
        options = MontageOptions(
            sampling_size=1,
            element_size=100,
            max_output_edge=1_000,
            max_output_pixels=1_000_000,
        )
        plan = plan_output_size(100, 100, options)
        self.assertEqual(plan.element_size, 10)
        self.assertEqual((plan.output_width, plan.output_height), (1_000, 1_000))
        self.assertTrue(plan.was_limited)

    def test_source_smaller_than_sampling_still_produces_one_cell(self):
        plan = plan_output_size(8, 5, MontageOptions(25, 12))
        self.assertEqual((plan.columns, plan.rows), (1, 1))
        self.assertEqual((plan.output_width, plan.output_height), (12, 12))

    def test_raised_limits_require_confirmation(self):
        with self.assertRaisesRegex(ValueError, "allow_large_output"):
            MontageOptions(1, 1, max_output_edge=10_001).validate()

    def test_partial_edges_are_included(self):
        image = np.zeros((3, 5, 3), dtype=np.uint8)
        image[:, 4] = (30, 60, 90)
        options = MontageOptions(2, 3)
        plan = plan_output_size(5, 3, options)
        colors = calculate_tile_colors(image, plan, "average")
        self.assertEqual(colors.shape, (2, 3, 3))
        np.testing.assert_array_equal(colors[0, 2], (30, 60, 90))


class MontagePipelineTests(unittest.TestCase):
    def test_matching_retains_threshold_fallback_and_seeded_variety(self):
        records = [
            ElementRecord("a", (0, 0, 1, 1), (10, 10, 10), (230, 230, 230)),
            ElementRecord("b", (0, 0, 1, 1), (15, 15, 15), (20, 20, 20)),
            ElementRecord("c", (0, 0, 1, 1), (230, 230, 230), (10, 10, 10)),
        ]
        colors = np.full((4, 10, 3), 12, dtype=np.uint8)
        colors[:, -1] = 180  # No threshold match; choose the closest material.
        for method, candidates, nearest in (
            ("average", {0, 1}, 2), ("most", {1, 2}, 0),
        ):
            with self.subTest(method=method):
                result = match_elements(colors, records, method, random_seed=17)
                self.assertEqual(set(result[:, :-1].flat), candidates)
                np.testing.assert_array_equal(result[:, -1], nearest)
                np.testing.assert_array_equal(
                    result, match_elements(colors, records, method, random_seed=17)
                )

    def test_each_selected_material_is_decoded_once(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            black_path = root / "black.png"
            white_path = root / "white.png"
            ImgTools.save_png(str(black_path), np.zeros((8, 8, 3), dtype=np.uint8))
            ImgTools.save_png(str(white_path), np.full((8, 8, 3), 255, dtype=np.uint8))

            index_path = root / "elements.txt"
            index_path.write_text(
                f"{black_path};{(0, 0, 8, 8)};{(0, 0, 0)};{(0, 0, 0)}\n"
                f"{white_path};{(0, 0, 8, 8)};{(255, 255, 255)};{(255, 255, 255)}\n",
                encoding="utf-8",
            )
            target = np.zeros((4, 4, 3), dtype=np.uint8)
            target[:, 2:] = 255
            output_path = root / "result.png"

            original_loader = ImgTools.pil_import_img_trans_cv2
            with patch.object(
                ImgTools,
                "pil_import_img_trans_cv2",
                wraps=original_loader,
            ) as loader:
                result = generate_montage(
                    target,
                    index_path,
                    output_path,
                    MontageOptions(2, 4, random_seed=7),
                )

            self.assertEqual(loader.call_count, 2)
            self.assertEqual(result.selected_element_count, 2)
            self.assertEqual((result.plan.output_width, result.plan.output_height), (8, 8))
            self.assertTrue(output_path.is_file())
            rendered = cv2.imread(str(output_path))
            self.assertEqual(rendered.shape, (8, 8, 3))


if __name__ == "__main__":
    unittest.main()
