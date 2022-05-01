import cv2
import os
import glob
import numpy as np
from utils.img_tools import ImgTools
from utils.list_processing import ListProcessing
from random import shuffle
from core.get_dir_data import GetDirImg
from utils.cal_img_data import CalImgData


def main():
    # 假設圖像 寬1200x高度1600 目標先切分成16張，每張300x400
    target_path = "./target_img/吾輩とお花見.png"
    org_img = ImgTools.pil_import_img_trans_cv2(target_path)
    p2p = 4

    img_height = org_img.shape[0]//p2p
    img_width = org_img.shape[1]//p2p
    resize_wh = (img_height, img_width)
    print(resize_wh)
    print(org_img.shape)  # (高,寬,通道數)

    # 定義顏色
    red_color = (0, 0, 255)
    # 繪製框線
    for i in range(p2p):
        for j in range(p2p):
            rec_left_up_point = (img_width * i, img_height * j)  # 分割左上角的點
            rec_right_down_point = (img_width * (i + 1), img_height * (j + 1))  # 分割右下角的點
            # cv2.rectangle(org_img, rec_left_up_point, rec_right_down_point, red_color, 2)
            x, y = rec_left_up_point
            w, h = (rec_right_down_point[0] - rec_left_up_point[0], rec_right_down_point[1] - rec_left_up_point[1])
            crop_img = org_img[y:y + h, x:x + w]  # 裁切下來做計算
            img_temp = crop_img.copy()
            img_temp, color = CalImgData.cal_img_pixel_frequency_color(img_temp)
            # img_temp, color = CalImgData.cal_img_average_color(img_temp)  # 取矩陣平均
            org_img[y:y + h, x:x + w] = img_temp  # 將色塊貼回原圖

    # # 取得圖像的元素清單
    # img_list = GetDirImg.get_dir_all_img(p2p, resize_wh)
    # # 將圖像清單以指定間隔n做分割，並生成清單組，該清單組每個元素是先前清單的n個資料為一組
    # # ex. new_img_list[0] = img_list[0:4]
    # new_img_list = list(ListProcessing.split_list_with_interval(img_list, p2p))
    # # 將清單內的圖像水平垂直拼接成大圖
    # img_tile = ImgTools.concat_vh(new_img_list)
    # print(img_tile.shape)
    # img_tile = cv2.addWeighted(org_img, 0.6, img_tile, 0.4, 0)
    # ImgTools.show_img(img_tile)
    # ImgTools.save_img("拉普拉斯", img_tile)

    ImgTools.show_img(org_img)


if __name__ == '__main__':
    import time
    start = time.time()
    main()
    end = time.time()
    print(end - start)
    # 待完成
    # 原始圖像mxn宮格 單位圖像顏色值 並模糊化處理
    # 單位圖像如何擷取，防止變形? 固定100x100?還是計算長寬 取中心? 最終生成一個txt紀錄資訊，就不用一直提取

