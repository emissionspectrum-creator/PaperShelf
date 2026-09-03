# PaperShelf

考題呈現平台：讓孩子在平板/電腦上看考卷題目，紙本作答。完整規格見 [DESIGN.md](DESIGN.md)。

## 使用方式

1. 把已裁切好的題目圖片放進 `source-images/`
2. 啟動打包器：
   - Ubuntu：雙擊桌面捷徑，或執行 `./start-packager.sh`
   - Windows 11：雙擊 `start-packager.bat`
   - 兩者都會自動開啟瀏覽器到 `http://localhost:8420`
3. 在打包器網頁中選圖、排序、逐題調整縮放，確認預覽後按「儲存」
4. 按「發布（git commit + push）」，將結果推上 GitHub，稍候 GitHub Pages 更新

## 目錄結構

```
DESIGN.md          完整規格文件（唯一依據）
manifest.json       考卷清單檔
source-images/      原始題目圖片（不會被公開發布邏輯以外的方式讀取）
packager/
  server.py          本機伺服器：檔案 I/O + git 指令代理
  static/            打包器網頁（HTML/CSS/JS）
docs/                GitHub Pages 發布根目錄
  index.html          考卷列表（由打包器產生，不手動編輯）
  exams/              每份考卷一個獨立 HTML 檔
```

## 已發布網站

https://emissionspectrum-creator.github.io/PaperShelf/
