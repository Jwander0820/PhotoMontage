import cv2
import glob
from random import shuffle
from utils.img_tools import ImgTools


class GetDirImg:
    @staticmethod
    def get_dir_all_img(resize_wh, p2p):
        """
        取得元素圖像資料夾下所有圖像資料
        :param resize_wh:
        :param p2p:
        :return:
        """
        img_height, img_width = resize_wh
        path = "./element_img/*"
        dirs = glob.glob(path)  # 提取資料夾圖片資料
        shuffle(dirs)
        img_list = []
        for i in range(p2p**2):
            # img = cv2.imread(dirs[i], cv2.IMREAD_COLOR)
            img = ImgTools.pil_import_img_trans_cv2(dirs[i])
            img = cv2.resize(img, (img_width, img_height))
            img_list.append(img)
        return img_list
