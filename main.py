import cv2
import numpy as np
from random import shuffle
from core.get_dir_data import GetDirImg
from utils.img_tools import ImgTools
from utils.cal_img_data import CalImgData
from utils.split_txt_data import SpiltTxtData


def main(target_img_path, save_img_name, org_img_pixel, element_img_pixel, element_img_data_path):
    org_img = ImgTools.pil_import_img_trans_cv2(target_img_path)  # 讀取底圖的原圖

    # org_img_pixel = 100  # 底圖採樣單位(n*n pixel取平均作為單位元素)
    # element_img_pixel = 100  # 單位元素圖片的大小(m*m pixel填充到新的圖片中)
    # 建議值200*200通常已經能看出是一張圖片了，填充圖像的尺寸越大(=越精細)，最終成品圖就越大，儲存時需要注意
    # ex.100*100的底圖，以20*20做分割就會分割成5*5的大方格，若設定填充圖片大小為200*200
    # 接下來會將元素圖片以200*200的大小貼在5*5對應的格子中，最終生成一張1000*1000大小的蒙太奇圖片
    resize_ratio = element_img_pixel//org_img_pixel
    # 計算底圖和填充圖片的縮放倍率，建議倍率的設定以穩定倍數為單位ex 1、2、5、10...(123/33還是能算啦但不曉得影響)
    mask_img = np.copy(org_img)
    montage_img = np.copy(org_img)
    montage_img = cv2.resize(montage_img, dsize=None, fx=resize_ratio, fy=resize_ratio)

    img_height_num = org_img.shape[0]//org_img_pixel
    img_width_num = org_img.shape[1]//org_img_pixel
    hw_num = (img_height_num, img_width_num)  # 分割底圖的高寬數
    print(hw_num)
    print(org_img.shape)  # (高,寬,通道數)

    # 讀取先前計算好的元素圖片資料，讀取到清單中，方便快速計算，不用重複多次讀寫真實圖片資料
    text = []
    with open(element_img_data_path, 'r') as f:
        for line in f:
            text.append(line)

    # 計算的主程式，循序計算高寬的資料
    # 內部流程為 1.計算底圖一個區塊(n*n)的平均顏色 2.將該平均顏色與元素圖片清單的平均顏色做計算，取歐式距離小於100的元素圖片加入清單
    # 3. 隨機選取清單內其中一張圖片作為元素填充至圖片(若清單為0則選取最接近的元素圖片)
    for i in range(img_width_num):
        for j in range(img_height_num):
            rec_left_up_point = (org_img_pixel * i, org_img_pixel * j)  # 分割左上角的點
            rec_right_down_point = (org_img_pixel * (i + 1), org_img_pixel * (j + 1))  # 分割右下角的點
            # cv2.rectangle(mask_img, rec_left_up_point, rec_right_down_point, (0, 0, 255), 2)  # 紅色分割線測試示意圖使用
            x, y = rec_left_up_point
            w, h = (rec_right_down_point[0] - rec_left_up_point[0], rec_right_down_point[1] - rec_left_up_point[1])
            crop_img = mask_img[y:y + h, x:x + w]  # 裁切下來做計算
            img_temp, color = CalImgData.cal_img_average_color(crop_img)  # 取矩陣平均
            mask_img[y:y + h, x:x + w] = img_temp  # 將色塊貼回原圖

            # 歐式距離計算顏色的相近程度(b1-b2)**2+(g1-g2)**2+(r1-r2)**2
            similar_color = [10000, 0]  # [距離,編號]紀錄最相近的顏色
            similar_color_list = []
            for k in range(len(text)):
                _, _, average_color, most_color = SpiltTxtData.split_img_resize_data(text[k])
                euclidean_distance = CalImgData.cal_color_euclidean_distance(color, average_color)
                if euclidean_distance < similar_color[0]:
                    similar_color[0] = euclidean_distance
                    similar_color[1] = k
                    if euclidean_distance < 100:  # 取顏色距離小於100編號的加入清單
                        similar_color_list.append(k)
            shuffle(similar_color_list)  # 清單內打亂順序
            print(similar_color_list)
            try:
                # 清單打亂後取第一個 = 取清單內隨機圖片
                file_path, crop_data, average_color, most_color = SpiltTxtData.split_img_resize_data(text[similar_color_list[0]])
            except:
                # 若清單內沒資料(表示沒有小於定值的資料)，則取顏色距離最短的圖片
                file_path, crop_data, average_color, most_color = SpiltTxtData.split_img_resize_data(text[similar_color[1]])

            crop_x, crop_y, crop_w, crop_h = crop_data  # 裁切資料
            img_temp = ImgTools.pil_import_img_trans_cv2(file_path)  # 讀取元素圖片
            img_temp = img_temp[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]  # 裁切元素圖片
            img_temp = cv2.resize(img_temp, (element_img_pixel, element_img_pixel))  # 縮放至指定大小
            x = element_img_pixel * i
            y = element_img_pixel * j
            montage_img[y:y + element_img_pixel, x:x + element_img_pixel] = img_temp  # 填充至指定區域

    # 顯示圖片，mask_img為n*n模糊化圖像，montage_img為蒙太奇拼接圖像，img_tile為模糊化圖像與拼接圖像在做融合，能有更佳的效果
    ImgTools.show_img(mask_img)
    ImgTools.show_img(montage_img)
    # 蒙版和原始蒙太奇圖像做比例融合，最終圖像會有更好一點的效果，也能選原始圖像做融合
    mask_img = cv2.resize(mask_img, dsize=None, fx=resize_ratio, fy=resize_ratio)
    img_tile = cv2.addWeighted(mask_img, 0.3, montage_img, 0.7, 0)
    ImgTools.show_img(img_tile)

    # 儲存圖像
    ImgTools.save_img(save_img_name, img_tile)


if __name__ == '__main__':
    # 取得元素圖像的資料，路徑,方形裁切資料,平均顏色，並記錄成txt，須執行過一次產生資料清單
    # dir_path = "./element_img"
    # specified_dir_data = "./element_img_data/element_img_square_data.txt"
    # GetDirImg.get_specified_dir_img_data(dir_path, specified_dir_data)
    # 測試用
    target_img_path = "./target_img/3x3_color_map.png"  # 作為底圖的路徑
    save_img_name = "測試"  # 儲存檔案名稱
    org_img_pixel = 100  # 底圖採樣單位(n*n pixel取平均作為單位元素)
    element_img_pixel = 200  # 單位元素圖片的大小(m*m pixel填充到新的圖片中)
    element_img_data_path = './element_img_data/element_img_square_data.txt'
    main(target_img_path, save_img_name, org_img_pixel, element_img_pixel, element_img_data_path)

    # target_img_path = "./target_img/Nyan_Cat.jpg"  # 作為底圖的路徑
    # save_img_name = "Nyan_Cat"  # 儲存檔案名稱
    # org_img_pixel = 20  # 底圖採樣單位(n*n pixel取平均作為單位元素)
    # element_img_pixel = 200  # 單位元素圖片的大小(m*m pixel填充到新的圖片中)
    # element_img_data_path = './element_img_data/meme_img_data.txt'
    # main(target_img_path, save_img_name, org_img_pixel, element_img_pixel, element_img_data_path)


