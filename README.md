# 🎧 MP3 網頁播放器

在瀏覽器裡播放 MP3（一次最多 5 首），每首歌曲都可以獨立調整 **音量** 與
**播放速度**。音樂來源有兩種：

1. **本機檔案**（預設）—— 選手機或電腦上的 `.mp3`，完全不上傳到伺服器，
   用瀏覽器內建的 `URL.createObjectURL()` 直接在本機播放，沒有大小限制
2. **Google 雲端硬碟連結** —— 貼上 Google 雲端硬碟「知道連結的使用者可檢視」
   的分享連結，直接從雲端硬碟串流播放，不用先下載到裝置

## 功能

- **本機檔案**：選好立刻可以播放，關閉分頁後需要重選
- **Google 雲端硬碟連結**：貼上分享連結（一次最多 5 個），可各自加顯示名稱
- 每首歌曲有自己的播放器，可獨立調整：
  - 🔊 音量（0% ～ 100%，iOS 上因系統限制無法用網頁調整，會改顯示提示）
  - ⏩ 播放速度（0.5x ～ 2x）
- 底部迷你播放列 + 「現正播放」全螢幕面板（大專輯圖示、進度條、上一首/下一首）
- 可選密碼保護整個網站（設定 `APP_PASSWORD` 環境變數後啟用登入頁）

### 使用 Google 雲端硬碟連結要注意

- 檔案要先在 Google 雲端硬碟設定共用權限為「知道連結的使用者」可檢視，
  否則瀏覽器連不到檔案
- 支援常見的分享連結格式，例如
  `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
- Google 對較大的檔案（約 25MB 以上）有時會顯示「無法掃描病毒」的提示頁面
  而不是直接給出檔案內容，這種情況下播放可能會失敗，建議大檔案改用「本機檔案」

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
- `templates/index.html` — 前端頁面，兩種音樂來源共用同一套播放器邏輯：
  - 本機檔案：選檔後用 `URL.createObjectURL(file)` 產生本機 Blob URL；
    換一批新檔案時會 `URL.revokeObjectURL()` 釋放舊的，避免分頁開久記憶體一直長
  - Google 雲端硬碟：從分享連結解析出檔案 ID，組成
    `https://drive.google.com/uc?export=download&id=FILE_ID` 直接當作
    `<audio>` 的 `src`，由瀏覽器直接向 Google 雲端硬碟串流播放
  - 音量／速度用 `<input type="range">` 綁定 `audio.volume` /
    `audio.playbackRate`（iOS 上 `volume` 會被系統忽略，改顯示提示文字）
- 關閉分頁或重新整理後，本機檔案的 Blob URL 會失效，需要重新選取；
  雲端硬碟連結則不受影響，重新整理後仍可貼上同樣連結播放

## 授權

個人專案，僅供自用。
