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
    target_path = "./target_img/吾輩とお花見_1080.png"
    org_img = ImgTools.pil_import_img_trans_cv2(target_path)
    montage_img = np.copy(org_img)

    img_pixel = 40  # 單位像素越小，效果越好
    # 現階段資料僅5199，4K圖片下 40*40需54*96=5184張圖片 (建議實驗用圖片先轉小吧==)

    img_height_num = org_img.shape[0]//img_pixel
    img_width_num = org_img.shape[1]//img_pixel
    resize_wh = (img_height_num, img_width_num)
    print(resize_wh)
    print(org_img.shape)  # (高,寬,通道數)

    f = open('element_img_square_data.txt')  # 開啟資料清單
    text = []
    for line in f:
        text.append(line)
    f.close()
    shuffle(text)
    # 定義顏色
    red_color = (0, 0, 255)
    # 繪製框線
    num = 0
    for i in range(img_width_num):
        for j in range(img_height_num):
            rec_left_up_point = (img_pixel * i, img_pixel * j)  # 分割左上角的點
            rec_right_down_point = (img_pixel * (i + 1), img_pixel * (j + 1))  # 分割右下角的點
            # cv2.rectangle(org_img, rec_left_up_point, rec_right_down_point, red_color, 2)  # 紅線分割示意
            x, y = rec_left_up_point
            w, h = (rec_right_down_point[0] - rec_left_up_point[0], rec_right_down_point[1] - rec_left_up_point[1])
            crop_img = org_img[y:y + h, x:x + w]  # 裁切下來做計算
            img_temp, color = CalImgData.cal_img_average_color(crop_img)  # 取矩陣平均
            org_img[y:y + h, x:x + w] = img_temp  # 將色塊貼回原圖

            # 目前為循序放置圖片，沒有演算==
            num += 1
            file_path = text[num].split(';')[0]  # 分號分隔取出檔案路徑
            crop_data = text[num].split(';')[1][1:-1].split(', ')  # 分號分隔取出裁切資料(去頭尾括號->逗點+空格分隔
            for k in range(len(crop_data)):  # 還要再把文字資料轉成int資料
                crop_data[k] = int(crop_data[k])
            print(crop_data)
            crop_x, crop_y, crop_w, crop_h = crop_data  # 裁切資料
            img_temp = ImgTools.pil_import_img_trans_cv2(file_path)
            img_temp = img_temp[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
            img_temp = cv2.resize(img_temp, (img_pixel, img_pixel))
            montage_img[y:y + h, x:x + w] = img_temp

    # # 取得圖像的元素清單
    # img_list = GetDirImg.get_dir_some_img_resize_rectangle(resize_wh)
    # # 將圖像清單以指定間隔n做分割，並生成清單組，該清單組每個元素是先前清單的n個資料為一組
    # # ex. new_img_list[0] = img_list[0:4]
    # new_img_list = list(ListProcessing.split_list_with_interval(img_list, p2p))
    # # 將清單內的圖像水平垂直拼接成大圖
    # img_tile = ImgTools.concat_vh(new_img_list)
    #
    # print(img_tile.shape)
    # img_tile = cv2.addWeighted(org_img, 0.6, img_tile, 0.4, 0)
    # ImgTools.show_img(img_tile)
    # ImgTools.save_img("拉普拉斯", img_tile)

    ImgTools.show_img(org_img)
    ImgTools.show_img(montage_img)
    img_tile = cv2.addWeighted(org_img, 0.6, montage_img, 0.4, 0)
    ImgTools.show_img(img_tile)

if __name__ == '__main__':
    import time
    start = time.time()
    main()
    end = time.time()
    print(end - start)
    # GetDirImg.get_dir_img_resize_square_data(5199)  # 取得元素圖像的資料，路徑,方形裁切資料,平均顏色

    # 待完成
    # 若單位圖片像素取值不是剛好的最後一排會漏空
    # 計算每張元素圖片的平均顏色
    # 計算每個位置的平均顏色，並以該顏色去尋找接近的圖像資料(如何演算?若該顏色僅1.2張圖片可以重複嗎?條件設置?)
    # 然後將圖片填到該區域的空位格上

    # 已完成
    # 原始圖像mxn宮格 單位圖像顏色值 並模糊化處理
    # 單位圖像如何擷取，防止變形? 固定100x100?還是計算長寬 取中心? 最終生成一個txt紀錄資訊，就不用一直提取