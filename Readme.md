# 圖像蒙太奇風格化
以指定圖像為基礎，將該圖像分割成 m x n個區塊，並在每個區塊中填入與該區域顏色相似的圖像，重新構築成一張蒙太奇風格化的圖像

 以下為範例的圖片，NyanCat的每個元素圖片都是由迷因組合而成的一張超大圖片

<div align=center>
<img src="example/Nyan_Cat_meme.gif"/>
</div>

# 程式範例
環境所需的套件可以參考requirement.txt；主要為numpy、OpenCV、Pillow

測試用資料清單已生成，直接執行main.py即可，檔案會輸出在montage_img資料夾下

**測試用資料版權皆非本人所有，僅提供測試使用，圖片來源皆為twitter公開圖源**

## 實際使用說明
1. 元素圖片的資料清單，取樣的檔案越多越好，顏色越豐富越好，若資料集較小，可能相同的顏色只會有一種元素圖片能放入，
最終成品圖會單調些。
2. 圖片參數設定，計算的底圖採樣單位通常越小越好，但如果取樣的太小，多數的顏色都是重複的，並且計算時間會大幅拉長，
且最終的成品圖檔會超乎想像的大。
   1. 因此在取樣上建議，設定一個模糊化後還是能大約看出整體圖像的參數。例如1080P的圖片縮放四分之一到
   270P，其實還是很能看出該圖像的內容，因此取樣的參數就能設為4 -> 每4x4的方格框選再一起計算顏色
   2. Ex. 100x100的圖像若取樣設為1，元素圖片大小設為100，代表計算圖像內所有的像素顏色，並將元素圖像以100x100 pixel
   大小填入最終成品圖， 最終成品圖將會是10000x10000 pixel大小的圖檔。

3. 圖片參數設定，元素圖片的大小建議值200x200通常已經能看出是一張圖片了，填充圖像的尺寸越大，
最終成品圖就越大(越精細)，但儲存時需要注意存儲空間。
   1. Ex.(main.py的範例) 300x300的底圖，以100x100做分割(設定n=100)就會分割成3x3的大方格，設定填充圖片大小為200x200
      (m=200)，接下來會將元素圖片以200x200的大小貼在3x3對應的格子中，最終生成一張600x600大小的蒙太奇圖片。
   2. **(作為參考，作者自己算的圖片NyanCat放大一百倍，最終是25000x25000的尺寸大小，檔案大小為530MB)**
4. 圖片參數設定，計算圖像的方法，預設為average計算平均顏色，若圖片資料庫數量不大，建議採平均顏色去計算，因為計算眾數顏色可能會因為資料庫不大，
只能找顏色偏更多的圖片替代，導致最後巨觀來看顏色偏差較大，而平均顏色至少能讓巨觀來看的顏色偏差較小，如果資料庫夠大 眾數顏色計算起來效果會更好。
### 前處理
1. 透過GetDirImg.get_specified_dir_img_data()，先取得要作為元素圖片的資料清單，完成的元素圖片資料清單，
會輸出在element_img_data資料夾下。

### 圖像處理
1. 選定要作為底圖的圖像，並提供路徑
2. 選定要提取的元素圖片資料清單，並提供路徑(*.txt)
3. 選定a. 底圖的採樣單位 b. 元素圖片的大小 c. 計算圖像的方法(average/most)
4. 輸入要儲存的檔案名稱，最終檔案會輸出在montage_img資料夾下


## 待優化
1. 若單位圖片像素取值不是剛好的最後一排會漏空(如果單位像素取的夠小可以忽略)
2. 在第一次爬取底圖時，應該可以順便紀錄每個單位像素的顏色資料，後續直接調用這個清單裡的顏色資料，與元素圖片清單做對應即可~!不用再計算一次底圖顏色!
3. 也許可以再多一層紀錄，把字典資料給保存下來，若是資料集沒有變更，下次就可以直接調用字典資料讓處理更快！現在是卡在顏色與元素圖片清單的計算時間較長

## 已解決問題
1. 原始圖像切分成mxn格，計算單位圖像顏色值，並模糊化處理
2. 單位圖像如何擷取，防止變形? 固定100x100?還是計算長寬 取中心? 最終生成一個txt紀錄資訊，就不用一直重複提取圖像資料
3. 計算每張元素圖片的平均顏色、眾數顏色
4. 計算每個位置的平均顏色，並以該顏色去尋找接近的圖像資料，然後將圖片填到該區域的空位上

    思路 : 尋找接近的顏色透過歐式距離算法找最接近的顏色，若距離小於1000就加入清單，然後清單內隨機挑選填在該區域空位，若清單為0則取距離最近的圖片。
5. 現階段仍相依原始圖像，應該可以設計成原始圖像以nxn做分割計算，然後填充圖像以n2xn2(較大的圖像)做填入
然後輸出一張超大的圖，讓填充圖像也能看得很清楚。 -> 已完成
6. 生成的清單在最後顏色的部分似乎偶爾會出現2個空格的問題，導致讀取有問題。優化元素圖片資料清單的紀錄和解析方式後已解決
7. 優化算法 : 建立重複顏色索引；先處理底圖，看底圖共有幾種顏色，建立集合，再將顏色種類與元素圖片清單做計算，
算出每種顏色對應的元素圖片資料，在循序計算底圖顏色，顏色在字典裡尋找對應的元素圖片資料!貼回蒙太奇
8. 優化輸出檔案命名規則