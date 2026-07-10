import re

class SpiltTxtData:
    @staticmethod
    def split_img_resize_data(img_data):
        """
        一次輸入一行，解析該行的四個資料，像素圖片路徑、方形裁切資料、裁切平均顏色、最多的顏色
        :param img_data:要解析的圖像資料
        :return:檔案路徑(str),裁切資訊(list),平均顏色(tuple),最多的顏色(tuple)
        """
        parts = img_data.split(';')
        file_path = parts[0]  # 分號分隔取出檔案路徑
        
        crop_nums = re.findall(r'-?\d+', parts[1])
        crop_data = [int(x) for x in crop_nums[-4:]]
        
        avg_nums = re.findall(r'-?\d+', parts[2])
        average_color_data = tuple(int(x) for x in avg_nums[-3:])
        
        most_nums = re.findall(r'-?\d+', parts[3])
        most_color_data = tuple(int(x) for x in most_nums[-3:])

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
