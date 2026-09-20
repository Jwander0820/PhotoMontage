"""Command-line entry point for the shared montage pipeline."""

import argparse
from pathlib import Path

from core.get_dir_data import GetDirImg
from core.montage_service import MontageOptions, generate_montage


def main(
    target_img_path,
    element_img_data_path,
    org_img_pixel,
    element_img_pixel,
    save_img_name,
    cal_color_method="average",
    max_output_edge=10_000,
    max_output_pixels=100_000_000,
    allow_large_output=False,
    random_seed=None,
):
    """Generate one montage and return its result metadata."""
    output_path = Path("./montage_img") / f"Montage_{save_img_name}.png"
    options = MontageOptions(
        sampling_size=int(org_img_pixel),
        element_size=int(element_img_pixel),
        color_method=cal_color_method,
        max_output_edge=int(max_output_edge),
        max_output_pixels=int(max_output_pixels),
        allow_large_output=bool(allow_large_output),
        random_seed=random_seed,
    )
    result = generate_montage(
        target_img_path,
        element_img_data_path,
        output_path,
        options,
    )
    plan = result.plan
    adjustment = "（已自動調整）" if plan.was_limited else ""
    print(
        f"輸出完成：{result.output_path}\n"
        f"尺寸：{plan.output_width} × {plan.output_height} {adjustment}\n"
        f"格線：{plan.columns} × {plan.rows}；"
        f"取樣 {plan.sampling_size}px；素材格 {plan.element_size}px\n"
        f"預估峰值記憶體：{plan.estimated_peak_memory_mb:.2f} MiB；"
        f"總耗時：{result.timings_ms['total'] / 1000:.2f} 秒"
    )
    return result


def _build_parser():
    parser = argparse.ArgumentParser(description="Generate photo montage artwork")
    parser.add_argument("target", nargs="?", default="./target_img/Nyan_Cat.png")
    parser.add_argument(
        "--elements",
        default="./element_img_data/element_img_square_data.txt",
        help="Material index text file",
    )
    parser.add_argument("--sampling", type=int, default=25)
    parser.add_argument("--tile", type=int, default=100)
    parser.add_argument("--method", choices=("average", "most"), default="average")
    parser.add_argument("--name", default="montage")
    parser.add_argument("--max-edge", type=int, default=10_000)
    parser.add_argument("--max-megapixels", type=int, default=100)
    parser.add_argument("--allow-large-output", action="store_true")
    parser.add_argument("--seed", type=int)
    return parser


if __name__ == "__main__":
    arguments = _build_parser().parse_args()
    element_index = Path(arguments.elements)
    if not element_index.exists() and Path("./element_img").is_dir():
        GetDirImg.get_specified_dir_img_data(
            "./element_img",
            str(element_index.resolve()),
        )
    main(
        arguments.target,
        str(element_index),
        arguments.sampling,
        arguments.tile,
        arguments.name,
        arguments.method,
        max_output_edge=arguments.max_edge,
        max_output_pixels=arguments.max_megapixels * 1_000_000,
        allow_large_output=arguments.allow_large_output,
        random_seed=arguments.seed,
    )
