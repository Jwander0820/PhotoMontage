"""Repeatable end-to-end benchmark for the optimized montage pipeline."""

import argparse
import random
import sys
import tempfile
from time import perf_counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.montage_service import MontageOptions, generate_montage
from core.processing_img import ProcessingImg
from core.rt_input_img_data import InputImgData
from utils.img_tools import ImgTools
from utils.split_txt_data import SpiltTxtData


def build_fixture(root: Path, material_count: int):
    material_dir = root / "materials"
    material_dir.mkdir()
    records = []
    for index in range(material_count):
        color = (
            (index * 47) % 256,
            (index * 83) % 256,
            (index * 131) % 256,
        )
        path = material_dir / f"material_{index:03d}.png"
        ImgTools.save_png(str(path), np.full((256, 256, 3), color, dtype=np.uint8))
        records.append(f"{path};{(0, 0, 256, 256)};{color};{color}\n")
    index_path = root / "elements.txt"
    index_path.write_text("".join(records), encoding="utf-8")
    return index_path


def run_legacy(target_path, index_path, output_path, sampling_size, element_size):
    started = perf_counter()
    mask, montage, rows, columns = InputImgData.rt_input_img_data(
        str(target_path), sampling_size, element_size
    )
    elements = InputImgData.rt_element_img_list(str(index_path))
    colors = ProcessingImg.cal_img_block_color_set(
        mask, sampling_size, columns, rows, cal_color_method="average"
    )
    matches = ProcessingImg.cal_img_block_color_dict(
        colors, elements, cal_color_method="average"
    )
    random.seed(17)
    for column in range(columns):
        for row in range(rows):
            _, color = ProcessingImg.cal_img_block_color(
                mask, sampling_size, column, row, cal_color_method="average"
            )
            selected = random.choice(matches[tuple(color)])
            path, crop, _, _ = SpiltTxtData.split_img_resize_data(elements[selected])
            ProcessingImg.crop_element_img_paste_montage_img(
                path, crop, montage, element_size, column, row
            )
    resized_mask = cv2.resize(mask, (montage.shape[1], montage.shape[0]))
    merged = cv2.addWeighted(resized_mask, 0.3, montage, 0.7, 0)
    ImgTools.save_png(str(output_path), merged)
    return (perf_counter() - started) * 1_000


def run_benchmark(image_size: int, material_count: int, repeat: int, compare_legacy: bool):
    generator = np.random.default_rng(20260711)
    target = generator.integers(0, 256, (image_size, image_size, 3), dtype=np.uint8)
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        index_path = build_fixture(root, material_count)
        target_path = root / "target.png"
        ImgTools.save_png(str(target_path), target)
        if compare_legacy:
            legacy_total = run_legacy(
                target_path,
                index_path,
                root / "legacy.png",
                sampling_size=20,
                element_size=40,
            )
            print(f"legacy total: {legacy_total:.2f} ms")
        totals = []
        for iteration in range(repeat):
            result = generate_montage(
                target,
                index_path,
                root / f"benchmark_{iteration}.png",
                MontageOptions(20, 40, random_seed=17),
            )
            totals.append(result.timings_ms["total"])
            print(f"run {iteration + 1}: {result.timings_ms}")
        print(f"best total: {min(totals):.2f} ms")
        if compare_legacy:
            print(f"speed-up: {legacy_total / min(totals):.2f}x")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-size", type=int, default=800)
    parser.add_argument("--materials", type=int, default=128)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--compare-legacy", action="store_true")
    arguments = parser.parse_args()
    run_benchmark(
        arguments.image_size,
        arguments.materials,
        arguments.repeat,
        arguments.compare_legacy,
    )
