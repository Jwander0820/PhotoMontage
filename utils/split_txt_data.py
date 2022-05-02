class SpiltTxtData:
    @staticmethod
    def split_img_resize_data(img_data):
        """
        一次輸入一行，解析該行的三個資料，像素圖片路徑、方形裁切資料、裁切平均顏色
        :param img_data:要解析的圖像資料
        :return:檔案路徑(str),裁切資訊(list),平均顏色(tuple)
        """
        file_path = img_data.split(';')[0]  # 分號分隔取出檔案路徑
        crop_data = img_data.split(';')[1]  # 分號分隔取出裁切資料
        average_color_data = img_data.split(';')[2]  # 分號分隔取出顏色資料

        crop_data = crop_data[1:-1].split(', ')  # 去頭尾括號再以逗點+空格分隔
        for k in range(4):  # 還要再把文字資料轉成int資料
            crop_data[k] = int(crop_data[k])
        # crop_x, crop_y, crop_w, crop_h = crop_data  # 裁切出來的資料(list)

        average_color_data = average_color_data[1:-2].split(' ')  # 去頭和尾\n+空格分隔
        for k in range(3):  # 還要再把文字資料轉成int資料
            average_color_data[k] = int(average_color_data[k])
        average_color_data = tuple(average_color_data)  # 轉成元組
        # b, g, r = average_color_data  # 裁切圖像的平均顏色

        return file_path, crop_data, average_color_data


if __name__ == '__main__':
    path = '../element_img_square_data.txt'
    text = []
    with open(path, 'r') as f:
        for line in f:
            text.append(line)
    print(text[1])
    for i in range(len(text)):
        path, crop, color = SpiltTxtData.split_img_resize_data(text[i])

    print(path)
    print(crop)
    print(color)

    print(type(path))
    print(type(crop))
    print(type(color))
