import numpy as np


class CalImgData:
    @staticmethod
    def cal_img_average_color(img):
        """
        傳入圖像，計算其平均顏色，回傳同樣大小矩形的純色圖像，和平均顏色
        :param img: 要計算平均顏色的圖像
        :return: 同樣大小矩形的純色圖像, 平均顏色
        """
        # 取矩陣平均，並回傳相同大小，單一色塊的矩形
        img_temp = img.copy()
        img_temp[:, :, 0], img_temp[:, :, 1], img_temp[:, :, 2] = np.average(img_temp, axis=(0, 1))
        color = img_temp[0][0][:]
        return img_temp, color

    @staticmethod
    def cal_img_pixel_frequency_color(img):
        """
        傳入圖像，計算其像素值頻率，回傳同樣大小矩形的純色圖像，和出現頻率最高的顏色(類似眾數概念)，計算時間較長一點
        :param img: 要計算眾數顏色的圖像
        :return: 同樣大小矩形的純色圖像, 眾數顏色
        """
        # 取矩陣平均，並回傳相同大小，單一色塊的矩形
        img_temp = img.copy()
        unique, counts = np.unique(img_temp.reshape(-1, 3), axis=0, return_counts=True)
        img_temp[:, :, 0], img_temp[:, :, 1], img_temp[:, :, 2] = unique[np.argmax(counts)]
        color = img_temp[0][0][:]
        return img_temp, color

    @staticmethod
    def cal_img_square_crop(img):
        """
        將圖像做方形置中框選，判斷圖像的高寬，判斷短邊為高或寬，並以短邊的值為最大方型框選，框選中心的圖像
        :param img:要框選的圖像
        :return:回傳框選資料，x,y,w,h，左上座標(x,y)，延伸寬高(w,h)
        """
        if len(img.shape) == 3:
            height, width, channel = img.shape
        else:
            height, width = img.shape
        if height == width:
            x = 0
            y = 0
            w = width
            h = height
        elif height < width:
            # new_img = (height, height)；橫向的圖片，高度方向為短邊
            left_up_point = (width - height) // 2
            x = left_up_point
            y = 0
            w = height
            h = height
        else:
            # new_img = (width, width)；直向的圖片，寬度方向為短邊
            left_up_point = (height - width) // 2
            x = 0
            y = left_up_point
            w = width
            h = width
        return x, y, w, h

    @staticmethod
    def cal_color_euclidean_distance(color1, color2):
        """
        計算兩個顏色的歐式距離，距離越近代表顏色越相似
        :param color1:要計算的顏色A
        :param color2:要計算的顏色B
        :return:回傳歐式距離之值
        """
        b1, g1, r1 = color1
        b2, g2, r2 = color2
        euclidean_distance = (b1 - b2) ** 2 + (g1 - g2) ** 2 + (r1 - r2) ** 2
        return euclidean_distance


if __name__ == '__main__':
    colorA = (255, 255, 0)
    colorB = (155, 255, 0)
    print(CalImgData.cal_color_euclidean_distance(colorA, colorB))
