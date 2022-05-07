import cv2
import glob
import os
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
    def get_element_img_data():
        """
        取得元素圖像資料夾(element_img)下所有圖像資料，並紀錄正方形裁切訊息成txt
        :return:True
        """
        folder_dir = "./element_img_data"
        if not os.path.exists(folder_dir):
            os.makedirs(folder_dir)
        path = "./element_img/*"
        txt_path = './element_img_data/element_img_square_data.txt'
        dirs = glob.glob(path)  # 提取資料夾圖片資料
        with open(txt_path, 'a') as f:
            for file in dirs:
                if '.tif' in file or '.png' in file or '.jpg' in file or '.jpeg' in file:
                    try:
                        img = ImgTools.pil_import_img_trans_cv2(file)
                        x, y, w, h = CalImgData.cal_img_square_crop(img)  # 元素圖像方形置中裁切資訊
                        img_crop = img[y:y+h, x:x+w]
                        img_crop = cv2.resize(img_crop, (200, 200))  # 縮小尺寸加速計算
                        _, average_color = CalImgData.cal_img_average_color(img_crop)  # 元素圖像平均顏色
                        _, most_color = CalImgData.cal_img_pixel_frequency_color(img_crop)  # 元素圖像最多的顏色
                        print(f'{file};{(x, y, w, h)};{tuple(average_color)};{tuple(most_color)}')
                        f.write(f'{file};{(x, y, w, h)};{tuple(average_color)};{tuple(most_color)}\n')
                    except:
                        None
        return True

    @staticmethod
    def get_specified_dir_img_data(dir_path, save_element_img_list_file_name):
        """
        取得指定資料夾下所有圖像資料，並紀錄正方形裁切訊息成txt
        :param dir_path: 元素圖像的資料夾路徑
        :param save_element_img_list_file_name: 儲存元素圖像資料的檔名
        :return:True
        """
        folder_dir = "./element_img_data"
        if not os.path.exists(folder_dir):
            os.makedirs(folder_dir)
        txt_path = os.path.join(folder_dir, save_element_img_list_file_name)  # 儲存資料清單的位置
        file_list = []
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for name in files:  # 取得路徑下所有檔案
                file_name = os.path.join(root, name)
                file_list.append(file_name)

        with open(txt_path, 'a') as f:
            for file in file_list:
                if '.tif' in file or '.png' in file or '.jpg' in file or '.jpeg' in file:
                    try:
                        img = ImgTools.pil_import_img_trans_cv2(file)
                        x, y, w, h = CalImgData.cal_img_square_crop(img)  # 元素圖像方形置中裁切資訊
                        img_crop = img[y:y + h, x:x + w]
                        img_crop = cv2.resize(img_crop, (200, 200))  # 縮小尺寸加速計算
                        _, average_color = CalImgData.cal_img_average_color(img_crop)  # 元素圖像平均顏色
                        _, most_color = CalImgData.cal_img_pixel_frequency_color(img_crop)  # 元素圖像最多的顏色
                        print(f'{file};{(x, y, w, h)};{tuple(average_color)};{tuple(most_color)}')
                        f.write(f'{file};{(x, y, w, h)};{tuple(average_color)};{tuple(most_color)}\n')
                    except:
                        None
        return True


if __name__ == '__main__':
    # 前處理element_img元素圖像資料夾下所有圖像資料
    # GetDirImg.get_element_img_data()
    dir_path = r"..\element_img"  # 讀取的資料夾路徑
    save_element_img_list_file_name = "example.txt"  # 元素圖片清單的檔名
    GetDirImg.get_specified_dir_img_data(dir_path, save_element_img_list_file_name)
