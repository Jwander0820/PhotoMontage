class DetectParam:
    @staticmethod
    def detect_cal_color_method(cal_color_method):
        """
        檢測參數:計算底圖顏色的方法是否為指定的方法，若非指定的方法，跳出主程式
        :param cal_color_method: 計算底圖顏色的方法
        :return: 若非指定的方法，回傳True
        """
        if cal_color_method == "average":
            return True
        elif cal_color_method == "most":
            return True
        else:
            return False


if __name__ == '__main__':
    color_method_list = ["average", "most", "area", "mass", 123]
    for color_method in color_method_list:
        if DetectParam.detect_cal_color_method(color_method):
            print(f"{color_method} 是指定計算顏色的方法")
        if not DetectParam.detect_cal_color_method(color_method):
            print(f"{color_method} 不是指定計算顏色的方法")
