import cv2
import random
from utils.img_tools import ImgTools
from utils.cal_img_data import CalImgData
from utils.split_txt_data import SpiltTxtData


class ProcessingImg:
    @staticmethod
    def cal_img_block_color(mask_img, org_img_pixel, i, j,
                            cal_color_method="average"):
        """
        1. 計算底圖色塊 - 平均顏色/眾數顏色
        :param mask_img: 蒙版圖像
        :param org_img_pixel: 底圖採樣單位
        :param i: 寬(x)
        :param j: 高(y)
        :param cal_color_method: 計算顏色的方法
        :return: 上色完蒙版圖像, 計算的顏色
        """
        x = org_img_pixel * i  # 左上角的點x
        y = org_img_pixel * j  # 左上角的點y
        w = org_img_pixel  # 寬度高度都為org_img_pixel
        h = org_img_pixel
        # cv2.rectangle(mask_img, (x, y), (x+w, y+h), (0, 0, 255), 2)  # 紅色分割線測試示意圖使用
        crop_img = mask_img[y:y + h, x:x + w]  # 裁切下來做計算
        if cal_color_method == "average":
            img_temp, color = CalImgData.cal_img_average_color(crop_img)  # 計算矩陣平均顏色
        elif cal_color_method == "most":
            img_temp, color = CalImgData.cal_img_pixel_frequency_color(crop_img)  # 取矩陣眾數顏色

        mask_img[y:y + h, x:x + w] = img_temp  # 將色塊貼回蒙版
        return mask_img, color

    @staticmethod
    def cal_color_distance(color, element_img_list, cal_color_method="average"):
        """
        2. 計算清單內的資料與底圖色塊的歐式距離 - 平均顏色/眾數顏色
        歐式距離計算顏色的相近程度(b1-b2)**2+(g1-g2)**2+(r1-r2)**2
        :param color: 要對比的顏色
        :param element_img_list: 元素圖像資料清單
        :param cal_color_method: 計算顏色的方法
        :return: 要裁切的檔案路徑,裁切資料的座標資訊,相似顏色清單
        """
        similar_color = [10000, 0]  # [距離,編號]紀錄最相近的顏色
        similar_color_list = []
        for k in range(len(element_img_list)):
            _, _, average_color, most_color = SpiltTxtData.split_img_resize_data(element_img_list[k])
            if cal_color_method == "average":
                euclidean_distance = CalImgData.cal_color_euclidean_distance(color, average_color)
            elif cal_color_method == "most":
                euclidean_distance = CalImgData.cal_color_euclidean_distance(color, most_color)
            if euclidean_distance < similar_color[0]:  # 比對所有資料，若較小的就替換掉先前的值
                similar_color[0] = euclidean_distance
                similar_color[1] = k
                if euclidean_distance < 1000:  # 取顏色距離小於1000的編號加入相似顏色清單
                    similar_color_list.append(k)
        try:
            # 取清單內隨機圖片
            file_path, crop_data, average_color, most_color = SpiltTxtData.split_img_resize_data(
                element_img_list[random.choice(similar_color_list)])
        except:
            # 若清單內沒資料(表示沒有小於定值的資料)，則取顏色距離最短的圖片
            file_path, crop_data, average_color, most_color = SpiltTxtData.split_img_resize_data(
                element_img_list[similar_color[1]])
            similar_color_list.append(similar_color[1])  # 若僅該顏色距離最近，加入至清單中
        # print(similar_color_list)
        return file_path, crop_data, similar_color_list

    @staticmethod
    def crop_element_img_paste_montage_img(file_path, crop_data, montage_img, element_img_pixel, i, j):
        """
        3. 裁切元素圖片，並貼到與蒙版圖像相同相對位置的蒙太奇圖像上
        :param file_path:要裁切的檔案路徑
        :param crop_data:裁切資料的座標資訊
        :param montage_img:蒙太奇圖像
        :param element_img_pixel:單位元素圖片的大小
        :param i: 寬(x)
        :param j: 高(y)
        :return: 回傳拼貼完(i,j)一塊的蒙太奇圖像
        """
        crop_x, crop_y, crop_w, crop_h = crop_data  # 裁切資料的座標資訊
        img_temp = ImgTools.pil_import_img_trans_cv2(file_path)  # 讀取元素圖片
        img_temp = img_temp[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]  # 裁切元素圖片
        img_temp = cv2.resize(img_temp, (element_img_pixel, element_img_pixel))  # 縮放至指定大小
        x = element_img_pixel * i
        y = element_img_pixel * j
        montage_img[y:y + element_img_pixel, x:x + element_img_pixel] = img_temp  # 填充至指定區域
        return montage_img

    @staticmethod
    def cal_img_block_color_set(mask_img, org_img_pixel, img_width_num, img_height_num,
                                cal_color_method="average"):
        """
        B1. 計算底圖色塊 - 平均顏色/眾數顏色，先循序爬取圖像，計算該圖像共有幾種顏色
        :param mask_img: 蒙版圖像
        :param org_img_pixel: 底圖採樣單位
        :param img_width_num: x軸方向切分區塊
        :param img_height_num: y軸方向切分區塊
        :param cal_color_method:計算底圖顏色的方法:平均顏色->average ; 眾數顏色->most，預設為average
        :return: 回傳底圖顏色種類的集合，代表這張圖像的所有顏色種類
        """
        color_list = []
        for i in range(img_width_num):
            for j in range(img_height_num):
                _, color = ProcessingImg.cal_img_block_color(
                    mask_img, org_img_pixel, i, j, cal_color_method=cal_color_method)
                color_list.append(tuple(color))
        color_set = set(color_list)  # 轉集合，排除掉重複的顏色
        return color_set

    @staticmethod
    def cal_img_block_color_dict(color_set, element_img_list, cal_color_method="average"):
        """
        B2. 計算底圖顏色種類與清單內的所有資料的歐式距離，並寫成字典形式，之後只要看到相同的顏色就不用再循序計算清單內資料，
        直接調用顏色對應的編號清單即可，在編號清單中隨機挑一個填入蒙太奇圖像中
        :param color_set: 底圖顏色種類的集合
        :param element_img_list: 元素圖片資料清單
        :param cal_color_method: 計算底圖顏色的方法:平均顏色->average ; 眾數顏色->most，預設為average
        :return: 回傳底圖顏色種類的對應元素圖片清單的字典
        """
        element_color_list = []
        for block_color in color_set:  # 取所有區塊顏色與元素圖片清單做計算
            _, _, similar_color_list = ProcessingImg.cal_color_distance(
                block_color, element_img_list, cal_color_method=cal_color_method)
            element_color_list.append(similar_color_list)
        block_color_dict = dict(zip(color_set, element_color_list))  # 把顏色種類與對應的元素圖片清單 合併成字典
        return block_color_dict
