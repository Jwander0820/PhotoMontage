import numpy as np


class CalImgData:
    @staticmethod
    def cal_img_average_color(img_temp):
        """
        傳入圖像，計算其平均顏色，回傳同樣大小矩形的純色圖像，和平均顏色
        :param img_temp: 要計算平均顏色的圖像
        :return: 同樣大小矩形的純色圖像, 平均顏色
        """
        # 取矩陣平均，並回傳相同大小，單一色塊的矩形
        img_temp[:, :, 0], img_temp[:, :, 1], img_temp[:, :, 2] = np.average(img_temp, axis=(0, 1))
        color = img_temp[0][0][:]
        return img_temp, color

    @staticmethod
    def cal_img_pixel_frequency_color(img_temp):
        """
        傳入圖像，計算其像素值頻率，回傳同樣大小矩形的純色圖像，和出現頻率最高的顏色(類似眾數概念)，計算時間較長一點
        :param img_temp: 要計算平均顏色的圖像
        :return: 同樣大小矩形的純色圖像, 平均顏色
        """
        # 取矩陣平均，並回傳相同大小，單一色塊的矩形
        unique, counts = np.unique(img_temp.reshape(-1, 3), axis=0, return_counts=True)
        img_temp[:, :, 0], img_temp[:, :, 1], img_temp[:, :, 2] = unique[np.argmax(counts)]
        color = img_temp[0][0][:]
        return img_temp, color

