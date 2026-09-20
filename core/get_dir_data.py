"""Material-directory scanning and legacy text-index generation."""

import glob
import os
from pathlib import Path
from random import shuffle
from tempfile import NamedTemporaryFile

import cv2

from utils.cal_img_data import CalImgData
from utils.img_tools import ImgTools


IMAGE_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}


class GetDirImg:
    @staticmethod
    def get_dir_some_img_resize_rectangle(resize_wh, number_of_pictures):
        img_height, img_width = resize_wh
        paths = glob.glob("./element_img/*")
        shuffle(paths)
        images = []
        for path in paths[:number_of_pictures]:
            image = ImgTools.pil_import_img_trans_cv2(path)
            images.append(cv2.resize(image, (img_width, img_height)))
        return images

    @staticmethod
    def get_element_img_data():
        return GetDirImg._write_index(
            "./element_img",
            "./element_img_data/element_img_square_data.txt",
        )

    @staticmethod
    def get_specified_dir_img_data(dir_path, save_element_img_list_file_name):
        os.makedirs("./element_img_data", exist_ok=True)
        output_path = os.path.join(
            "./element_img_data",
            save_element_img_list_file_name,
        )
        return GetDirImg._write_index(dir_path, output_path)

    @staticmethod
    def _write_index(dir_path, output_path):
        if not os.path.isdir(dir_path):
            raise ValueError(f"素材資料夾不存在：{dir_path}")

        def raise_scan_error(error):
            raise error

        image_paths = []
        for root, _, files in os.walk(dir_path, onerror=raise_scan_error):
            for name in files:
                path = os.path.join(root, name)
                if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                    image_paths.append(path)
        image_paths.sort()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        indexed_count = 0
        temporary_path = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=output_path.parent,
                prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
            ) as destination:
                temporary_path = Path(destination.name)
                for path in image_paths:
                    try:
                        image = ImgTools.pil_import_img_trans_cv2(path)
                        x, y, width, height = CalImgData.cal_img_square_crop(image)
                        crop = image[y : y + height, x : x + width]
                        preview = cv2.resize(crop, (200, 200), interpolation=cv2.INTER_AREA)
                        average = tuple(
                            int(channel)
                            for channel in CalImgData.get_img_average_color(preview)
                        )
                        most = tuple(
                            int(channel)
                            for channel in CalImgData.get_img_pixel_frequency_color(preview)
                        )
                    except (OSError, ValueError, cv2.error) as exc:
                        print(f"Skipping unreadable material {path}: {exc}")
                        continue
                    # Let write failures abort the scan, preserving the old index.
                    destination.write(
                        f"{path};{(x, y, width, height)};{average};{most}\n"
                    )
                    indexed_count += 1
            if indexed_count:
                os.replace(temporary_path, output_path)
            return indexed_count > 0
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    GetDirImg.get_specified_dir_img_data(
        r"..\element_img",
        "example.txt",
    )
