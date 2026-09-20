"""Shared, memory-conscious photo montage generation pipeline."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from math import ceil, isqrt
from os import PathLike
from pathlib import Path
from random import Random
from time import perf_counter
from typing import Union

import cv2
import numpy as np

from utils.img_tools import ImgTools
from utils.split_txt_data import SpiltTxtData


DEFAULT_MAX_OUTPUT_EDGE = 10_000
DEFAULT_MAX_OUTPUT_PIXELS = 100_000_000
COLOR_DISTANCE_THRESHOLD = 1_000
TargetSource = Union[str, PathLike[str], np.ndarray]


@dataclass(frozen=True)
class MontageOptions:
    sampling_size: int
    element_size: int
    color_method: str = "average"
    max_output_edge: int = DEFAULT_MAX_OUTPUT_EDGE
    max_output_pixels: int = DEFAULT_MAX_OUTPUT_PIXELS
    allow_large_output: bool = False
    random_seed: int | None = None
    png_compression: int = 1

    def validate(self) -> None:
        integer_fields = {
            "sampling_size": self.sampling_size,
            "element_size": self.element_size,
            "max_output_edge": self.max_output_edge,
            "max_output_pixels": self.max_output_pixels,
        }
        for name, value in integer_fields.items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.color_method not in {"average", "most"}:
            raise ValueError("color_method must be 'average' or 'most'")
        if not 0 <= self.png_compression <= 9:
            raise ValueError("png_compression must be between 0 and 9")
        raises_default_limit = (
            self.max_output_edge > DEFAULT_MAX_OUTPUT_EDGE
            or self.max_output_pixels > DEFAULT_MAX_OUTPUT_PIXELS
        )
        if raises_default_limit and not self.allow_large_output:
            raise ValueError(
                "Large output limits require allow_large_output confirmation"
            )


@dataclass(frozen=True)
class OutputPlan:
    source_width: int
    source_height: int
    requested_sampling_size: int
    requested_element_size: int
    sampling_size: int
    element_size: int
    columns: int
    rows: int
    output_width: int
    output_height: int
    output_pixels: int
    raw_memory_mb: float
    estimated_peak_memory_mb: float
    was_limited: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ElementRecord:
    path: str
    crop: tuple[int, int, int, int]
    average_color: tuple[int, int, int]
    most_color: tuple[int, int, int]


@dataclass(frozen=True)
class MontageResult:
    output_path: str
    plan: OutputPlan
    selected_element_count: int
    timings_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = self.plan.to_dict()
        data.update(
            {
                "output_path": self.output_path,
                "selected_element_count": self.selected_element_count,
                "timings_ms": self.timings_ms,
                "grid": {"columns": self.plan.columns, "rows": self.plan.rows},
                "effective_sampling_size": self.plan.sampling_size,
                "effective_element_size": self.plan.element_size,
            }
        )
        return data


def plan_output_size(width: int, height: int, options: MontageOptions) -> OutputPlan:
    """Return an output plan that stays within both edge and pixel budgets."""
    options.validate()
    if width <= 0 or height <= 0:
        raise ValueError("Source image dimensions must be positive")

    sampling_size = options.sampling_size
    # Establish a close lower bound when even one-pixel output tiles would exceed
    # the configured budgets. The short correction loop handles ceil rounding.
    sampling_size = max(
        sampling_size,
        ceil(width / options.max_output_edge),
        ceil(height / options.max_output_edge),
        ceil((width * height / options.max_output_pixels) ** 0.5),
    )

    while True:
        columns = ceil(width / sampling_size)
        rows = ceil(height / sampling_size)
        if (
            columns <= options.max_output_edge
            and rows <= options.max_output_edge
            and columns * rows <= options.max_output_pixels
        ):
            break
        sampling_size += 1

    cell_count = columns * rows
    max_tile_by_edge = min(
        options.max_output_edge // columns,
        options.max_output_edge // rows,
    )
    max_tile_by_pixels = isqrt(options.max_output_pixels // cell_count)
    element_size = min(
        options.element_size,
        max_tile_by_edge,
        max_tile_by_pixels,
    )
    if element_size < 1:
        raise ValueError("Output limits are too small for even a one-pixel tile")

    output_width = columns * element_size
    output_height = rows * element_size
    output_pixels = output_width * output_height
    raw_memory_mb = output_pixels * 3 / (1024**2)

    return OutputPlan(
        source_width=width,
        source_height=height,
        requested_sampling_size=options.sampling_size,
        requested_element_size=options.element_size,
        sampling_size=sampling_size,
        element_size=element_size,
        columns=columns,
        rows=rows,
        output_width=output_width,
        output_height=output_height,
        output_pixels=output_pixels,
        raw_memory_mb=round(raw_memory_mb, 2),
        # PNG encoding can temporarily require another output-sized buffer.
        estimated_peak_memory_mb=round(raw_memory_mb * 2.15, 2),
        was_limited=(
            sampling_size != options.sampling_size
            or element_size != options.element_size
        ),
    )


def load_element_index(element_data_path: str | PathLike[str]) -> list[ElementRecord]:
    """Parse the legacy text index once and ignore records whose files vanished."""
    records: list[ElementRecord] = []
    with open(element_data_path, "r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                path, crop, average, most = SpiltTxtData.split_img_resize_data(line)
                if len(crop) != 4 or not Path(path).is_file():
                    continue
                records.append(
                    ElementRecord(
                        path=path,
                        crop=tuple(crop),
                        average_color=tuple(average),
                        most_color=tuple(most),
                    )
                )
            except (IndexError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid element index record at line {line_number}"
                ) from exc
    if not records:
        raise ValueError("Element image index contains no readable images")
    return records


def calculate_tile_colors(
    image: np.ndarray,
    plan: OutputPlan,
    color_method: str,
) -> np.ndarray:
    """Calculate every target tile color exactly once."""
    sampling_size = plan.sampling_size
    rows, columns = plan.rows, plan.columns

    if (
        color_method == "average"
        and image.shape[0] % sampling_size == 0
        and image.shape[1] % sampling_size == 0
    ):
        reshaped = image.reshape(
            rows,
            sampling_size,
            columns,
            sampling_size,
            3,
        )
        return reshaped.mean(axis=(1, 3)).astype(np.uint8)

    colors = np.empty((rows, columns, 3), dtype=np.uint8)
    for row in range(rows):
        y0 = row * sampling_size
        y1 = min(y0 + sampling_size, image.shape[0])
        for column in range(columns):
            x0 = column * sampling_size
            x1 = min(x0 + sampling_size, image.shape[1])
            block = image[y0:y1, x0:x1]
            if color_method == "average":
                colors[row, column] = np.asarray(cv2.mean(block)[:3], dtype=np.uint8)
            else:
                colors[row, column] = _most_frequent_color(block)
    return colors


def _most_frequent_color(image: np.ndarray) -> np.ndarray:
    pixels = image.reshape(-1, 3).astype(np.uint32, copy=False)
    packed = pixels[:, 0] | (pixels[:, 1] << 8) | (pixels[:, 2] << 16)
    values, counts = np.unique(packed, return_counts=True)
    selected = int(values[int(np.argmax(counts))])
    return np.asarray(
        [selected & 255, (selected >> 8) & 255, (selected >> 16) & 255],
        dtype=np.uint8,
    )


def match_elements(
    tile_colors: np.ndarray,
    records: list[ElementRecord],
    color_method: str,
    random_seed: int | None = None,
) -> np.ndarray:
    """Match target colors in bounded NumPy batches, then randomize per tile."""
    flattened = tile_colors.reshape(-1, 3)
    unique_colors, inverse, counts = np.unique(
        flattened, axis=0, return_inverse=True, return_counts=True
    )
    element_colors = np.asarray(
        [
            record.average_color if color_method == "average" else record.most_color
            for record in records
        ],
        dtype=np.int32,
    )
    # Group destinations once so candidates can be consumed and discarded for
    # each color, rather than retaining up to colors * materials indices.
    positions = np.argsort(inverse, kind="stable")
    boundaries = np.concatenate(([0], np.cumsum(counts)))
    selected = np.empty(len(flattened), dtype=np.intp)
    randomizer = Random(random_seed)

    # Keep diff + squared-distance working arrays near 32 MiB combined.
    batch_size = max(1, min(len(unique_colors), 1_000_000 // len(records)))
    for start in range(0, len(unique_colors), batch_size):
        stop = min(start + batch_size, len(unique_colors))
        target_batch = unique_colors[start:stop].astype(np.int32)
        diff = target_batch[:, None, :] - element_colors[None, :, :]
        distances = np.einsum("ijk,ijk->ij", diff, diff, optimize=True)
        for offset, row_distances in enumerate(distances):
            candidates = np.flatnonzero(row_distances < COLOR_DISTANCE_THRESHOLD)
            if candidates.size == 0:
                candidates = np.asarray([int(np.argmin(row_distances))], dtype=np.intp)
            color_index = start + offset
            destinations = positions[boundaries[color_index] : boundaries[color_index + 1]]
            if candidates.size == 1:
                selected[destinations] = candidates[0]
            else:
                selected[destinations] = np.fromiter(
                    (candidates[randomizer.randrange(len(candidates))] for _ in destinations),
                    dtype=np.intp,
                    count=len(destinations),
                )
    return selected.reshape(tile_colors.shape[:2])


def compose_montage(
    tile_colors: np.ndarray,
    selected_elements: np.ndarray,
    records: list[ElementRecord],
    plan: OutputPlan,
) -> tuple[np.ndarray, int]:
    """Decode each selected material once and blend directly into final output."""
    output = np.empty(
        (plan.output_height, plan.output_width, 3),
        dtype=np.uint8,
    )
    placements: dict[int, list[int]] = defaultdict(list)
    for flat_position, element_index in enumerate(selected_elements.reshape(-1)):
        placements[int(element_index)].append(flat_position)

    for element_index, positions in placements.items():
        record = records[element_index]
        source = ImgTools.pil_import_img_trans_cv2(record.path)
        crop_x, crop_y, crop_width, crop_height = record.crop
        x0 = max(0, crop_x)
        y0 = max(0, crop_y)
        x1 = min(source.shape[1], crop_x + crop_width)
        y1 = min(source.shape[0], crop_y + crop_height)
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"Invalid crop data for material: {record.path}")
        cropped = source[y0:y1, x0:x1]
        interpolation = (
            cv2.INTER_AREA
            if cropped.shape[0] >= plan.element_size
            and cropped.shape[1] >= plan.element_size
            else cv2.INTER_CUBIC
        )
        tile = cv2.resize(
            cropped,
            (plan.element_size, plan.element_size),
            interpolation=interpolation,
        )

        for flat_position in positions:
            row, column = divmod(flat_position, plan.columns)
            y0 = row * plan.element_size
            x0 = column * plan.element_size
            destination = output[
                y0 : y0 + plan.element_size,
                x0 : x0 + plan.element_size,
            ]
            destination[:] = tile_colors[row, column]
            cv2.addWeighted(tile, 0.7, destination, 0.3, 0, dst=destination)

        del source, cropped, tile

    return output, len(placements)


def generate_montage(
    target: TargetSource,
    element_data_path: str | PathLike[str],
    output_path: str | PathLike[str],
    options: MontageOptions,
) -> MontageResult:
    """Generate and save a montage without persistent material thumbnails."""
    total_start = perf_counter()
    options.validate()

    stage_start = perf_counter()
    if isinstance(target, np.ndarray):
        target_image = np.ascontiguousarray(target)
    else:
        target_image = ImgTools.pil_import_img_trans_cv2(str(target), apply_exif_orientation=True)
    if target_image.ndim != 3 or target_image.shape[2] != 3:
        raise ValueError("Target image must contain three color channels")
    plan = plan_output_size(target_image.shape[1], target_image.shape[0], options)
    records = load_element_index(element_data_path)
    load_ms = (perf_counter() - stage_start) * 1_000

    stage_start = perf_counter()
    tile_colors = calculate_tile_colors(target_image, plan, options.color_method)
    analyze_ms = (perf_counter() - stage_start) * 1_000
    del target_image

    stage_start = perf_counter()
    selected = match_elements(
        tile_colors,
        records,
        options.color_method,
        options.random_seed,
    )
    match_ms = (perf_counter() - stage_start) * 1_000

    stage_start = perf_counter()
    output, selected_element_count = compose_montage(
        tile_colors,
        selected,
        records,
        plan,
    )
    compose_ms = (perf_counter() - stage_start) * 1_000

    stage_start = perf_counter()
    output_path = str(output_path)
    ImgTools.save_png(output_path, output, compression=options.png_compression)
    encode_ms = (perf_counter() - stage_start) * 1_000
    total_ms = (perf_counter() - total_start) * 1_000

    timings = {
        "load": round(load_ms, 2),
        "analyze": round(analyze_ms, 2),
        "match": round(match_ms, 2),
        "compose": round(compose_ms, 2),
        "encode": round(encode_ms, 2),
        "total": round(total_ms, 2),
    }
    return MontageResult(
        output_path=output_path,
        plan=plan,
        selected_element_count=selected_element_count,
        timings_ms=timings,
    )
