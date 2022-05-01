import cv2
import os
import glob
from utils.img_tools import ImgTools
from utils.list_processing import ListProcessing
from random import shuffle


def concat_vh(list_2d):
    # return final image
    return cv2.vconcat([cv2.hconcat(list_h)
                        for list_h in list_2d])

def main():
    # 假設圖像 寬1200x高度1600 目標先切分成16張，每張300x400
    target_path = "./target_img/吾輩とお花見.png"
    org_img = ImgTools.pil_import_img_trans_cv2(target_path)
    p2p = 40

    img_height = org_img.shape[0]//p2p
    img_width = org_img.shape[1]//p2p
    print(img_height, img_width)
    print(org_img.shape)  # (高,寬,通道數)

    # 定義顏色
    red_color = (0, 0, 255)
    # 繪製框線
    # for i in range(p2p + 1):
    #     for j in range(p2p + 1):
    #         rec_left_up_point = (img_width * i, img_height * i)
    #         rec_right_down_point = (img_width * (i + 1), img_height * j)
    #         cv2.rectangle(org_img, rec_left_up_point, rec_right_down_point, red_color, 10)

    path = "./element_img/*"
    dirs = glob.glob(path)  # 提取資料夾圖片資料
    shuffle(dirs)
    img_list = []
    for i in range(p2p**2):
        # img = cv2.imread(dirs[i], cv2.IMREAD_COLOR)
        img = ImgTools.pil_import_img_trans_cv2(dirs[i])
        img = cv2.resize(img, (img_width, img_height))
        img_list.append(img)

    # 將圖像清單以指定間隔n做分割，並生成清單組，該清單組每個元素是先前清單的n個資料為一組
    # ex. new_img_list[0] = img_list[0:4]
    new_img_list = list(ListProcessing.split_list_with_interval(img_list, p2p))

    img_tile = concat_vh(new_img_list)
    # img_tile = concat_vh([img_list[p2p * 0:p2p * 1],
    #                       img_list[p2p * 1:p2p * 2],
    #                       img_list[p2p * 2:p2p * 3],
    #                       img_list[p2p * 3:p2p * 4]])
    print(img_tile.shape)
    img_tile = cv2.addWeighted(org_img, 0.6, img_tile, 0.4, 0)
    ImgTools.show_img(img_tile)

if __name__ == '__main__':
    main()

