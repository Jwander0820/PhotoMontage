import numpy as np
import cv2
from utils.img_tools import ImgTools


class InputImgData:
    @staticmethod
    def rt_input_img_data(target_img_path, org_img_pixel, element_img_pixel):
        """
        回傳輸入圖片的相關資料
        :param target_img_path: str;作為底圖的路徑
        :param org_img_pixel: int;底圖採樣單位(n*n pixel取平均作為單位元素)
        :param element_img_pixel: int;單位元素圖片的大小(m*m pixel填充到新的圖片中)
        :return: 蒙版圖像、蒙太奇圖像、
        """
        org_img = ImgTools.pil_import_img_trans_cv2(target_img_path)  # 讀取底圖的原圖
        # 計算底圖和填充圖片的縮放倍率，建議倍率的設定以穩定倍數為單位ex 1、2、5、10...(123/33還是能算啦但不曉得影響)
        resize_ratio = element_img_pixel // org_img_pixel  # 計算元素圖片和原始圖像的縮放比例
        mask_img = np.copy(org_img)  # 複製一份原始尺寸蒙版圖像
        montage_img = np.copy(org_img)  # 複製一份蒙版圖像並縮放到需要的倍率
        montage_img = cv2.resize(montage_img, dsize=None, fx=resize_ratio, fy=resize_ratio)

        img_height_num = org_img.shape[0] // org_img_pixel  # Y(高度)方向元素圖片數量
        img_width_num = org_img.shape[1] // org_img_pixel  # X(寬度)方向元素圖片數量
        print(f"x軸方向切分{img_width_num}個區塊")  # 分割底圖的高寬數=將n*m的圖片填充至蒙太奇圖片中
        print(f"y軸方向切分{img_height_num}個區塊")
        # print(org_img.shape)  # 原圖.shape(高,寬,通道數)
        return mask_img, montage_img, img_height_num, img_width_num

    @staticmethod
    def rt_element_img_list(element_img_data_path):
        """
        讀取先前計算好的元素圖片資料，讀取到清單中，方便快速計算，不用重複多次讀寫真實圖片資料
        :param element_img_data_path: str;元素圖片的資料清單路徑，預設資料清單會儲存在element_img_data資料夾下
        :return: 元素圖片資料清單
        """
        text = []
        with open(element_img_data_path, 'r') as f:
            for line in f:
                text.append(line)
        return text
