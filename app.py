import hashlib
import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from core.get_dir_data import GetDirImg
from core.montage_service import (
    DEFAULT_MAX_OUTPUT_EDGE,
    DEFAULT_MAX_OUTPUT_PIXELS,
    MontageOptions,
    generate_montage,
)
from utils.img_tools import ImgTools


app = Flask(__name__)

TARGET_IMG_DIR = Path("./target_img")
ELEMENT_IMG_DIR = Path("./element_img")
MONTAGE_IMG_DIR = Path("./montage_img")
ELEMENT_DATA_DIR = Path("./element_img_data")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

for directory in (
    TARGET_IMG_DIR,
    MONTAGE_IMG_DIR,
    ELEMENT_DATA_DIR,
    ELEMENT_IMG_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)


def _ensure_sample_materials() -> None:
    has_images = any(
        path.suffix.lower() in IMAGE_EXTENSIONS for path in ELEMENT_IMG_DIR.iterdir()
    )
    if has_images:
        return
    print("Auto-generating 128 test color blocks for startup...")
    try:
        from generate_test_elements import generate_color_blocks

        generate_color_blocks(str(ELEMENT_IMG_DIR), 128)
        print("Success: Generated 128 test color blocks.")
    except Exception as exc:
        print(f"Warning: Could not auto-generate test elements: {exc}")


if os.environ.get("PHOTOMONTAGE_SKIP_SAMPLE_MATERIALS") != "1":
    _ensure_sample_materials()


def get_element_data_file(element_dir: str) -> Path:
    abs_path = os.path.abspath(element_dir)
    directory_hash = hashlib.md5(abs_path.encode("utf-8")).hexdigest()[:8]
    folder_name = "".join(
        character
        for character in os.path.basename(abs_path)
        if character.isalnum() or character in ("_", "-")
    )
    return ELEMENT_DATA_DIR / f"cache_{folder_name or 'dir'}_{directory_hash}.txt"


def _form_int(name: str, default: int) -> int:
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必須是整數") from exc


def _build_options() -> MontageOptions:
    max_megapixels = _form_int(
        "max_output_megapixels",
        DEFAULT_MAX_OUTPUT_PIXELS // 1_000_000,
    )
    allow_large_output = request.form.get("allow_large_output", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return MontageOptions(
        sampling_size=_form_int("org_img_pixel", 25),
        element_size=_form_int("element_img_pixel", 100),
        color_method=request.form.get("cal_color_method", "average"),
        max_output_edge=_form_int("max_output_edge", DEFAULT_MAX_OUTPUT_EDGE),
        max_output_pixels=max_megapixels * 1_000_000,
        allow_large_output=allow_large_output,
    )


def _resolve_predefined_image(filename: str) -> Path:
    candidate = (TARGET_IMG_DIR / Path(filename).name).resolve()
    if candidate.parent != TARGET_IMG_DIR.resolve() or not candidate.is_file():
        raise ValueError("找不到指定的預設圖片")
    return candidate


def _ensure_element_index(element_dir: str) -> Path:
    directory = Path(element_dir)
    if not directory.is_dir():
        raise ValueError(f"素材資料夾不存在：{element_dir}")
    index_path = get_element_data_file(element_dir)
    if not index_path.is_file() or index_path.stat().st_size == 0:
        GetDirImg.get_specified_dir_img_data(element_dir, index_path.name)
    if not index_path.is_file() or index_path.stat().st_size == 0:
        raise ValueError("素材資料庫為空，請加入圖片後重新掃描")
    return index_path


@app.route("/")
def index():
    target_images = sorted(
        path.name
        for path in TARGET_IMG_DIR.iterdir()
        if path.suffix.lower() in IMAGE_EXTENSIONS
    )
    return render_template(
        "index.html",
        target_images=target_images,
        default_max_output_edge=DEFAULT_MAX_OUTPUT_EDGE,
        default_max_output_megapixels=DEFAULT_MAX_OUTPUT_PIXELS // 1_000_000,
    )


@app.route("/api/update_elements", methods=["POST"])
def update_elements():
    try:
        element_dir = request.form.get("element_dir", str(ELEMENT_IMG_DIR))
        if not Path(element_dir).is_dir():
            return jsonify({"error": f"素材資料夾不存在：{element_dir}"}), 400

        index_path = get_element_data_file(element_dir)
        if not GetDirImg.get_specified_dir_img_data(element_dir, index_path.name):
            return jsonify({"error": "沒有可讀取的素材圖片，原有索引已保留。"}), 400
        with index_path.open("r", encoding="utf-8") as source:
            count = sum(1 for line in source if line.strip())
        return jsonify(
            {
                "success": True,
                "count": count,
                "message": f"素材索引已更新，共 {count} 張圖片。",
            }
        )
    except Exception as exc:
        app.logger.exception("Unable to update material index")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/montage", methods=["POST"])
def run_montage():
    try:
        options = _build_options()
        options.validate()
        element_dir = request.form.get("element_dir", str(ELEMENT_IMG_DIR))
        upload = request.files.get("image_file")
        if upload and upload.filename:
            target = ImgTools.decode_image_bytes(upload.read())
        else:
            predefined_image = request.form.get("predefined_img", "")
            if not predefined_image:
                raise ValueError("請上傳圖片或選擇預設圖片")
            target = _resolve_predefined_image(predefined_image)

        element_index = _ensure_element_index(element_dir)
        result_id = uuid.uuid4().hex[:12]
        output_filename = f"Montage_web_{result_id}.png"
        output_path = MONTAGE_IMG_DIR / output_filename
        result = generate_montage(
            target,
            element_index,
            output_path,
            options,
        )

        response = result.to_dict()
        response.pop("output_path", None)
        response.update(
            {
                "success": True,
                "result_url": f"/montage_img/{output_filename}",
            }
        )
        return jsonify(response)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except MemoryError:
        return jsonify(
            {"error": "記憶體不足，請提高取樣尺寸或降低輸出限制。"}
        ), 413
    except Exception as exc:
        app.logger.exception("Unable to generate montage")
        return jsonify({"error": str(exc)}), 500


@app.route("/montage_img/<path:filename>")
def serve_montage_img(filename):
    return send_from_directory(MONTAGE_IMG_DIR, filename)


@app.route("/target_img/<path:filename>")
def serve_target_img(filename):
    return send_from_directory(TARGET_IMG_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
