# 🎧 MP3 網頁播放器

選取手機或電腦上的 MP3 檔案（一次最多 5 首），直接在瀏覽器裡播放，每首歌曲
都可以獨立調整 **音量** 與 **播放速度**。**檔案完全不會上傳到伺服器** ——
選取後用瀏覽器內建的 `URL.createObjectURL()` 直接在本機播放，音檔資料從頭
到尾只留在使用者的裝置上，沒有大小限制，也不用等上傳。

## 功能

- 選取本機 `.mp3` 檔案（一次最多 5 首），完全不上傳，選好立刻可以播放
- 每首歌曲有自己的播放器，可獨立調整：
  - 🔊 音量（0% ～ 100%，iOS 上因系統限制無法用網頁調整，會改顯示提示）
  - ⏩ 播放速度（0.5x ～ 2x）
- 底部迷你播放列 + 「現正播放」全螢幕面板（大專輯圖示、進度條、上一首/下一首）
- 可選密碼保護整個網站（設定 `APP_PASSWORD` 環境變數後啟用登入頁）

## 本機執行

```bash
pip install -r requirements.txt
python app.py
```

預設監聽 `http://localhost:5060`（可用 `PORT` 環境變數調整）。

### 環境變數

| 變數            | 說明                                   | 預設值                 |
|-----------------|----------------------------------------|-------------------------|
| `PORT`          | 監聽埠號                               | `5060`                   |
| `APP_PASSWORD`  | 設定後開啟登入頁保護整個網站           | 無（不啟用）             |
| `SECRET_KEY`    | Flask session 加密金鑰                 | 隨機產生                 |

## 用 Docker 執行

```bash
docker build -t mp3-web-player .
docker run -p 5060:5060 mp3-web-player
```

## 架構筆記

- `app.py` — 極簡的 Flask 主程式：只負責回應首頁 HTML 與可選的密碼保護
  （登入 / 登出），沒有任何檔案上傳或儲存相關的路由，音檔完全不經過伺服器
- `templates/index.html` — 前端頁面，選檔後用 `URL.createObjectURL(file)`
  產生本機 Blob URL 交給單一 `Audio` 物件播放；換一批新檔案時會
  `URL.revokeObjectURL()` 釋放舊的，避免分頁開久了記憶體一直長。
  音量／速度用 `<input type="range">` 綁定 `audio.volume` /
  `audio.playbackRate`（iOS 上 `volume` 會被系統忽略，改顯示提示文字）
- 關閉分頁或重新整理後，瀏覽器會釋放 Blob URL，需要重新選取檔案

## 授權

個人專案，僅供自用。
