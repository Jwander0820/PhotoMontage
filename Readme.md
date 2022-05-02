# 圖像蒙太奇風格化
以指定圖像為基礎，將該圖像分割成 m x n個區塊，並在每個區塊中填入與該區域顏色相似的圖像，重新構築成一張蒙太奇風格化的圖像

測試用資料清單已生成，直接執行main.py即可，檔案會輸出在montage_img資料夾下


### 待處理問題
1. 若單位圖片像素取值不是剛好的最後一排會漏空(如果單位像素取的夠小可以忽略)


2. 生成的清單在最後顏色的部分似乎偶爾會出現2個空格的問題，導致讀取有問題，待處理現階段先用記事本ctrl+R取代處理了
   
    問題原因：若color_data的值小於3位數會以空白填充。 ex. (111,123,142) -> 正常
   ( 87, 10,  9) -> 不正常，因為讀取時也會讀到空格，會讓str轉int時產生錯誤。待處理
    

### 待優化
1. 重複的像素應該可以直接記錄起來，不用每次都讀取整個清單做循序計算。 
    #### 處理思路->可以先循序處理底圖內所有區域的平均顏色，並記錄下來共有幾種顏色(通常鄰近區塊內都會一樣，只需紀錄"一種"即可)
    #### 再以該顏色與元素圖片清單內的顏色做計算，計算出每種顏色對應的元素圖片清單，之後在依照顏色填入對應元素圖片即可

### 已解決問題
1. 原始圖像mxn格，計算單位圖像顏色值，並模糊化處理
2. 單位圖像如何擷取，防止變形? 固定100x100?還是計算長寬 取中心? 最終生成一個txt紀錄資訊，就不用一直提取
3. 計算每張元素圖片的平均顏色
4. 計算每個位置的平均顏色，並以該顏色去尋找接近的圖像資料(如何演算?若該顏色僅1.2張圖片可以重複嗎?條件設置?)然後將圖片填到該區域的空位上
    #### 尋找接近的顏色透過歐式距離算法找最接近的顏色，若距離小於100就加入清單，然後清單內隨機挑選填在該區域空位，若清單為0則取距離最近的圖片
5. 現階段仍相依原始圖像，應該可以設計成原始圖像以nxn做分割計算，然後填充圖像以n2xn2(較大的圖像)做填入
然後輸出一張超大的圖，讓填充圖像也能看得很清楚。 -> 已完成