class SpiltTxtData:
    @staticmethod
    def split_img_resize_data(img_data):
        """
        一次輸入一行，解析該行的四個資料，像素圖片路徑、方形裁切資料、裁切平均顏色、最多的顏色
        :param img_data:要解析的圖像資料
        :return:檔案路徑(str),裁切資訊(list),平均顏色(tuple),最多的顏色(tuple)
        """
        file_path = img_data.split(';')[0]  # 分號分隔取出檔案路徑
        crop_data = img_data.split(';')[1]  # 分號分隔取出裁切資料
        average_color_data = img_data.split(';')[2]  # 分號分隔取出平均顏色資料
        most_color_data = img_data.split(';')[3]  # 分號分隔取出最多顏色資料

        crop_data = crop_data[1:-1].split(', ')  # 去頭尾括號再以逗點+空格分隔
        for k in range(4):  # 還要再把文字資料轉成int資料
            crop_data[k] = int(crop_data[k])
        # crop_x, crop_y, crop_w, crop_h = crop_data  # 裁切出來的資料(list)

        average_color_data = average_color_data[1:-1].split(', ')  # 去頭尾括號再以逗點+空格分隔
        for k in range(3):  # 還要再把文字資料轉成int資料
            average_color_data[k] = int(average_color_data[k])
        average_color_data = tuple(average_color_data)  # 轉成元組
        # b, g, r = average_color_data  # 裁切圖像的平均顏色

        most_color_data = most_color_data[1:-2].split(', ')  # 去頭和尾\n 再以逗點+空格分隔
        for k in range(3):  # 還要再把文字資料轉成int資料
            most_color_data[k] = int(most_color_data[k])
        most_color_data = tuple(most_color_data)  # 轉成元組
        # b, g, r = average_color_data  # 裁切圖像的平均顏色

        return file_path, crop_data, average_color_data, most_color_data


if __name__ == '__main__':
    path = '../element_img_data/element_img_square_data.txt'
    text = []
    with open(path, 'r') as f:
        for line in f:
            text.append(line)
    # for i in range(len(text)):
    #     path, crop, average_color, most_color = SpiltTxtData.split_img_resize_data(text[i])

    path, crop, average_color, most_color = SpiltTxtData.split_img_resize_data(text[0])
    print(text[0])

    print(path)
    print(crop)
    print(average_color)
    print(most_color)

    print(type(path))
    print(type(crop))
    print(type(average_color))
    print(type(most_color))
