# PhotoMontage 工作台

將目標圖片切成色彩區塊，再以素材庫中顏色接近的圖片重新拼成蒙太奇作品。專案同時提供 Flask 網頁工作台與命令列入口，兩者共用相同的尺寸保護與高效合成核心。

![Nyan Cat montage example](example/Nyan_Cat_meme.gif)

## 安裝與啟動

建議使用 Python 3.12：

```powershell
python -m pip install -r requirement.txt
python app.py
```

接著開啟 `http://127.0.0.1:5000`。

網頁流程：

1. 指定包含素材圖片的本機資料夾，按下「掃描並更新索引」。
2. 上傳目標圖片或選擇範例。
3. 調整取樣邊長、素材格邊長與色彩方式。
4. 在 OUTPUT MAP 確認實際尺寸與記憶體估算後生成。

## 速度與資源行為

- 掃描素材庫時只讀取圖片並在 `element_img_data` 寫入色彩及裁切座標索引，不會複製素材原圖。
- 合成前會一次算完所有目標格色彩與素材配對；同一張被選素材在一次工作中最多開啟、解碼、裁切及縮放一次。
- 素材配對按批次計算並立即釋放候選清單，避免相近色素材很多時累積大量記憶體。
- 素材索引先寫入暫存檔，掃描完成才替換；掃描失敗或沒有可讀圖片時保留原有索引。
- 素材依序處理，貼完即釋放，不建立永久縮圖快取。
- 網頁上傳圖直接由請求內容解碼，不會永久寫入 `target_img`。
- 上傳與本機目標圖片統一套用 EXIF 方向，避免手機直拍照片在不同入口出現旋轉差異；素材仍使用既有索引的座標系。
- 生成結果會永久保留在 `montage_img`，需要時可自行刪除。

最終 RGB 圖片的基本記憶體約為：

```text
寬 × 高 × 3 bytes
```

10000×10000 的單張 RGB 陣列約為 286 MiB。儲存 PNG 時還會暫時產生編碼緩衝，因此介面以約 2.15 倍原始陣列顯示保守尖峰估算。

## 輸出尺寸保護

預設同時限制：

- 單邊最大 10000 像素。
- 總輸出最大 100 百萬像素。

若要求的輸出超過限制，程式會先降低實際素材格尺寸；若每格縮到 1 像素仍超限，才提高取樣邊長以減少格數。小圖片不會為了填滿上限而被自動放大。

可在「輸出安全限制」提高預設值，但必須勾選大型輸出風險確認。右側與下側不足一個完整取樣區塊的內容仍會保留，不會產生空白邊。

## 命令列

```powershell
python main.py target_img/Nyan_Cat.png `
  --elements element_img_data/element_img_square_data.txt `
  --sampling 25 `
  --tile 100 `
  --method average `
  --name nyan-cat
```

常用限制參數：

```text
--max-edge 10000
--max-megapixels 100
--allow-large-output
```

執行後會顯示實際輸出尺寸、格數、有效取樣參數、記憶體估算及各階段耗時。

## 測試與效能基準

```powershell
python -m unittest discover -s tests -v
node --test tests/test_frontend.cjs
python benchmarks/benchmark_montage.py --compare-legacy
python benchmarks/benchmark_matching.py
```

基準會使用固定亂數建立暫存素材，分別量測載入、色彩分析、配對、合成與 PNG 編碼，不會在專案內留下測試圖片。
