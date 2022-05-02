class ListProcessing:
    @staticmethod
    def split_list_with_interval(split_list, n):
        """
        將輸入的清單分割為間隔為n的清單
        :param split_list:要分割的清單
        :param n:將清單分割為每個矩陣有n個元素
        :return:分割好的清單
        """
        # 將list分割 (l:list, n:每個matrix裡面有n個元素)
        for idx in range(0, len(split_list), n):
            yield split_list[idx:idx + n]
