import cv2
import glob
from random import shuffle
from utils.img_tools import ImgTools
from utils.cal_img_data import CalImgData


class GetDirImg:
    @staticmethod
    def get_dir_some_img_resize_rectangle(resize_wh, number_of_pictures):
        """
        取得元素圖像資料夾下所有圖像資料，並resize成指定大小
        :param resize_wh:resize的高度和寬度(h,w)
        :param number_of_pictures:要取幾張圖片
        :return:回傳選取完resize完的圖像資料清單
        """
        img_height, img_width = resize_wh
        path = "./element_img/*"
        dirs = glob.glob(path)  # 提取資料夾圖片資料
        shuffle(dirs)
        img_list = []
        for i in range(number_of_pictures):
            img = ImgTools.pil_import_img_trans_cv2(dirs[i])
            img = cv2.resize(img, (img_width, img_height))
            img_list.append(img)
        return img_list

    @staticmethod
    def get_dir_img_resize_square_data():
        """
        取得元素圖像資料夾下所有圖像資料，並紀錄正方形裁切訊息成txt
        :return:True
        """
        path = "./element_img/*"
        txt_path = './element_img_square_data.txt'
        dirs = glob.glob(path)  # 提取資料夾圖片資料
        with open(txt_path, 'a') as f:
            for file in dirs:
                if '.tif' in file or '.png' in file or '.jpg' in file:
                    img = ImgTools.pil_import_img_trans_cv2(file)
                    x, y, w, h = CalImgData.cal_img_square_crop(img)  # 元素圖像方形置中裁切資訊
                    img_crop = img[y:y+h, x:x+w]
                    _, color = CalImgData.cal_img_average_color(img_crop)  # 元素圖像平均顏色
                    f.write(f'{file};{(x, y, w, h)};{color}\n')
        return True


if __name__ == '__main__':
    # 前處理element_img元素圖像資料夾下所有圖像資料
    GetDirImg.get_dir_img_resize_square_data()
