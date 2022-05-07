import os.path
import sys
from core.get_dir_data import GetDirImg
from core.processing_img import *
from core.rt_input_img_data import *
from utils.img_tools import ImgTools
from utils.detect_param import DetectParam


def main(target_img_path, element_img_data_path, org_img_pixel, element_img_pixel,
         save_img_name, cal_color_method="average"):
    """
    蒙太奇圖像處理主程式
    element_img_pixel建議值200*200通常已經能看出是一張圖片了，填充圖像的尺寸越大(=越精細)，最終成品圖就越大，儲存時需要注意
    ex.300*300的底圖，以100*100做分割(設定n=100)就會分割成3*3的大方格，若設定填充圖片大小為200*200
    接下來會將元素圖片以200*200的大小貼在3*3對應的格子中，最終生成一張600*600大小的蒙太奇圖片
    :param target_img_path: str;作為底圖的路徑
    :param element_img_data_path: str;元素圖片的資料清單路徑，預設資料清單會儲存在element_img_data資料夾下
    :param org_img_pixel: int;底圖採樣單位(n*n pixel取平均作為單位元素)
    :param element_img_pixel: int;單位元素圖片的大小(m*m pixel填充到新的圖片中)
    :param save_img_name: str;要儲存的檔名，成品檔會輸出在montage_img資料夾下
    :param cal_color_method: 計算底圖顏色的方法:平均顏色->average ; 眾數顏色->most，預設為average
    :return:None
    """
    if not DetectParam.detect_cal_color_method(cal_color_method):  # 檢測是否為指定的計算顏色方式
        print(f"{cal_color_method} 不是指定計算顏色的方法")
        sys.exit(1)
    # 回傳輸入圖片的相關資料
    mask_img, montage_img, img_height_num, img_width_num = \
        InputImgData.rt_input_img_data(target_img_path, org_img_pixel, element_img_pixel)
    # 回傳元素圖像清單
    element_img_list = InputImgData.rt_element_img_list(element_img_data_path)
    # 計算的主程式，循序計算高寬的資料
    # 內部流程為 1.計算底圖一個區塊(n*n)的平均顏色 2.將該平均顏色與元素圖片清單的平均顏色做計算，取歐式距離小於1000的元素圖片加入清單
    # 3. 隨機選取清單內其中一張圖片作為元素填充至圖片(若清單為0則選取最接近的元素圖片)
    for i in range(img_width_num):
        for j in range(img_height_num):
            # 1. 計算底圖色塊 - 平均顏色/眾數顏色
            mask_img, color = ProcessingImg.\
                cal_org_average_color(mask_img, org_img_pixel, i, j, cal_color_method=cal_color_method)
            # 2. 計算清單內的資料與底圖色塊的歐式距離
            file_path, crop_data = ProcessingImg.\
                cal_color_distance(color, element_img_list)
            # 3. 裁切元素圖片，並貼到與蒙版圖像相同相對位置的蒙太奇圖像上
            montage_img = ProcessingImg.\
                crop_element_img_paste_montage_img(file_path, crop_data, montage_img, element_img_pixel, i, j)

    # 蒙版和原始蒙太奇圖像做比例融合，最終圖像會有更好一點的效果，也能選原始圖像做融合
    mask_img_resize = cv2.resize(mask_img, (montage_img.shape[1], montage_img.shape[0]))
    merge_img = cv2.addWeighted(mask_img_resize, 0.3, montage_img, 0.7, 0)
    # 顯示圖片，mask_img為n*n模糊化圖像，montage_img為蒙太奇拼接圖像，img_tile為模糊化圖像與拼接圖像在做融合，能有更佳的效果
    ImgTools.show_img(mask_img)
    ImgTools.show_img(montage_img)
    ImgTools.show_img(merge_img)
    # 儲存圖像
    ImgTools.save_img(save_img_name, merge_img)


if __name__ == '__main__':
    # 取得元素圖像的資料，路徑,方形裁切資料,平均顏色，並記錄成txt，須執行過一次產生資料清單
    if not os.path.exists("./element_img_data/element_img_square_data.txt"):
        dir_path = "./element_img"  # 讀取的資料夾路徑
        specified_dir_data = "element_img_square_data.txt"  # 儲存元素圖片清單的檔名
        GetDirImg.get_specified_dir_img_data(dir_path, specified_dir_data)

    # 測試用範例程式
    target_img_path = "./target_img/3x3_color_map.png"  # 作為底圖的路徑
    element_img_data_path = './element_img_data/element_img_square_data.txt'  # 元素圖像資料清單的路徑
    org_img_pixel = 100  # 底圖採樣單位(n*n pixel取平均作為單位元素)
    element_img_pixel = 200  # 單位元素圖片的大小(m*m pixel填充到新的圖片中)
    save_img_name = "測試"  # 儲存檔案名稱
    cal_color_method = "average"  # 計算底圖顏色的方法，若無指定預設為average，可選擇average或most
    main(target_img_path,
         element_img_data_path,
         org_img_pixel,
         element_img_pixel,
         save_img_name,
         cal_color_method)

    # target_img_path = "./target_img/Nyan_Cat.jpg"
    # element_img_data_path = './element_img_data/meme_img_data.txt'
    # save_img_name = "Nyan_Cat"
    # org_img_pixel = 20
    # element_img_pixel = 200
    # cal_color_method = "most"
    # main(target_img_path, element_img_data_path, org_img_pixel, element_img_pixel, save_img_name, cal_color_method)
