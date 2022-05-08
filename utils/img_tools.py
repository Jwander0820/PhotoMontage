import cv2
import os
import numpy as np
from PIL import Image


class ImgTools:

    @staticmethod
    def show_img(img):
        """
        以視窗的形式展現圖片，視窗大小為圖片的一半
        若圖片太大，直接用cv2.imshow會以完整解析度呈現，所以改用下面的nameWindow把圖像放在裡面限制大小
        :param img: 要顯示的圖像
        :return: None
        """
        # 冷知識:在imshow顯示的時候，可以在選定的窗口中做圖片的複製(Ctrl+C)與保存(Ctrl+S)
        cv2.namedWindow("windows", 0)
        # 設定窗口大小，("名稱", x, y) x是寬度 y是高度，此處暫以縮小一半作呈現
        cv2.resizeWindow("windows", int(img.shape[1] / 2), int(img.shape[0] / 2))
        cv2.imshow("windows", img)
        cv2.waitKey()
        cv2.destroyAllWindows()

    @staticmethod
    def save_img(file_name, img, org_img_pixel, element_img_pixel, cal_color_method):
        """
        儲存圖像
        :param file_name:儲存的檔名
        :param img:要儲存的圖像資料
        :param org_img_pixel: 底圖採樣單位
        :param element_img_pixel: 單位元素圖片的大小
        :param cal_color_method: 計算底圖顏色的方法:平均顏色->average ; 眾數顏色->most，預設為average
        :return: None
        """
        zoom_ratio = element_img_pixel // org_img_pixel  # 計算縮放倍率
        dir_path = f"./montage_img"
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        # Saving the image 儲存圖片
        filename = f'{dir_path}/Montage_{file_name}_ZoomRatio-{zoom_ratio}_' \
                   f'ElementImgSize-{element_img_pixel}_Method-{cal_color_method}.png'
        # imencode，好處是能寫入中文名稱
        cv2.imencode('.png', img, [int(cv2.IMWRITE_TIFF_RESUNIT), 2,  # 解析度單位
                                   int(cv2.IMWRITE_TIFF_COMPRESSION), 5,  # 壓縮方式
                                   int(cv2.IMWRITE_TIFF_XDPI), 600,  # 設定水平dpi
                                   int(cv2.IMWRITE_TIFF_YDPI), 600,  # 設定垂直dpi
                                   ])[1].tofile(filename)

    @staticmethod
    def pil_import_img_trans_cv2(file_path):
        """
        透過PIL匯入圖片並轉換成cv2格式傳出
        :param file_path: 要讀取的圖片路徑
        :return: 回傳cv2形式的圖像資料
        """
        img = Image.open(file_path)  # 使用PIL讀取檔案，避開cv2無法讀取中文路徑的問題
        pil2cv2 = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        return pil2cv2

    @staticmethod
    def concat_vh(list_2d):
        """
        將二維清單依照順序水平垂直拼接起來，先拼接水平再垂直
        :param list_2d: 要拼接的圖片清單
        :return: 拼接的圖像結果
        """
        # return final image
        # 下方的拼接結果即是同張圖以3x3九宮格排列拼接
        # img_tile = concat_vh([[img1_s, img1_s, img1_s],
        #                       [img1_s, img1_s, img1_s],
        #                       [img1_s, img1_s, img1_s]])
        return cv2.vconcat([cv2.hconcat(list_h)
                            for list_h in list_2d])
