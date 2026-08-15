# 🎧 MP3 網頁播放器

在瀏覽器裡播放 MP3（一次最多 5 首），每首歌曲都可以獨立調整 **音量** 與
**播放速度**。音樂來源有三種：

> 👉 只是想知道怎麼「使用」這個網站（不是要架設/改程式），
> 請直接看 **[使用說明.md](使用說明.md)**。以下是給開發者/架設者看的技術文件。

1. **本機檔案**（預設）—— 選手機或電腦上的 `.mp3`，完全不上傳到伺服器，
   用瀏覽器內建的 `URL.createObjectURL()` 直接在本機播放，沒有大小限制
2. **登入 Google 帳號** —— 用 OAuth 授權後，直接從自己的雲端硬碟搜尋、
   勾選檔案播放，**不需要事先把檔案設成公開分享**
3. **Google 雲端硬碟分享連結** —— 貼上「知道連結的使用者可檢視」的分享連結，
   不登入帳號也能播放已公開分享的檔案

## 功能

- **本機檔案**：選好立刻可以播放，關閉分頁後需要重選
- **登入 Google 帳號**：授權後可搜尋、勾選最多 5 首雲端硬碟裡的 MP3；
  播放時由伺服器代理向 Google Drive API 要資料（帶你自己的授權），
  檔案完全不需要公開分享，也不會經過我方以外的第三方
- **雲端硬碟分享連結**：貼上分享連結（一次最多 5 個），可各自加顯示名稱
- 每首歌曲有自己的播放器，可獨立調整：
  - 🔊 音量（0% ～ 100%，iOS 上因系統限制無法用網頁調整，會改顯示提示）
  - ⏩ 播放速度（0.5x ～ 3x，以 0.1 為間隔）
  - ⏪⏩ 快轉／倒轉 20 秒
- 底部迷你播放列 + 「現正播放」全螢幕面板（大專輯圖示、進度條、上一首/下一首）
- 可選密碼保護整個網站（設定 `APP_PASSWORD` 環境變數後啟用登入頁）

### 設定「登入 Google 帳號」功能

這個功能需要你自己在 Google Cloud Console 建立一個 OAuth 用戶端（免費），
沒設定的話網站仍可正常運作，只是會提示改用「貼上分享連結」的方式。

1. 打開 [Google Cloud Console](https://console.cloud.google.com/) → 建立一個新專案（或選現有的）
2. 「API 和服務」→「已啟用的 API 和服務」→「啟用 API 和服務」→ 搜尋
   **Google Drive API** → 啟用
3. 「API 和服務」→「OAuth 同意畫面」→ User Type 選 **外部（External）**
   → 填基本資訊（App 名稱、你的信箱）即可，不需要送審
   - 「測試使用者」加入你自己的 Google 帳號 email
4. 「API 和服務」→「憑證」→「建立憑證」→「OAuth 用戶端 ID」
   → 應用程式類型選 **網頁應用程式**
   - 「已授權的重新導向 URI」填：`https://你的網域/auth/google/callback`
     （本機測試則是 `http://localhost:5060/auth/google/callback`）
5. 建立後會拿到 **用戶端 ID** 和 **用戶端密鑰**，設到下面的環境變數
   `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`

> App 保持在「測試中」狀態即可，不需要送 Google 審核；但測試中狀態的
> refresh token 大約 7 天會過期，過期後只要重新按一次「使用 Google 帳號登入」
> 就好。如果想避免這個限制，可以把 OAuth 同意畫面的發布狀態改成
> 「已上線」（不用通過驗證也能設定），登入時瀏覽器會顯示「Google 未驗證這個應用程式」
> 的警告，點擊「繼續」即可（因為這是你自己的 App）。

### 使用雲端硬碟分享連結要注意

- 檔案要先在 Google 雲端硬碟設定共用權限為「知道連結的使用者」可檢視，
  否則瀏覽器連不到檔案
- 支援常見的分享連結格式，例如
  `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
- Google 對某些檔案會顯示「無法掃描病毒」的提示頁面而不是直接給出檔案內容，
  這種情況下播放可能會失敗——遇到這個問題可以改用「登入 Google 帳號」的方式，
  因為那個方式是透過官方 API 用你自己的授權直接取檔案，不會遇到這個提示頁

### 檔案大小限制

- 本站程式碼本身沒有對雲端硬碟的檔案設任何大小上限
- 「貼分享連結」的方式會受 Google 前面提到的「無法掃描病毒」提示頁影響，
  檔案越大越容易遇到，沒有固定的大小門檻
- 「登入 Google 帳號」的方式走官方 Drive API 直接串流，沒有大小限制

## 本機執行

```bash
pip install -r requirements.txt
python app.py
```

預設監聽 `http://localhost:5060`（可用 `PORT` 環境變數調整）。

### 環境變數

| 變數                    | 說明                                       | 預設值                 |
|-------------------------|--------------------------------------------|-------------------------|
| `PORT`                  | 監聽埠號                                   | `5060`                   |
| `APP_PASSWORD`          | 設定後開啟登入頁保護整個網站               | 無（不啟用）             |
| `SECRET_KEY`            | Flask session 加密金鑰                     | 隨機產生                 |
| `GOOGLE_CLIENT_ID`      | Google OAuth 用戶端 ID（見上方設定步驟）   | 無（不啟用登入功能）     |
| `GOOGLE_CLIENT_SECRET`  | Google OAuth 用戶端密鑰                    | 無（不啟用登入功能）     |

## 用 Docker 執行

```bash
docker build -t mp3-web-player .
docker run -p 5060:5060 mp3-web-player
```

## 架構筆記

- `app.py` — Flask 主程式：可選的密碼保護、Google OAuth 登入流程
  （`/auth/google/login` → Google 同意畫面 → `/auth/google/callback` 換 token）、
  Google Drive API 代理（列出檔案 `/api/drive/list`、串流檔案內容
  `/api/drive/stream/<id>`，會轉發 `Range` header 支援拖曳進度）。
  OAuth token 存在伺服器記憶體裡（不放進瀏覽器 cookie），伺服器重啟後需要
  使用者重新登入一次 Google；本機檔案播放完全不經過伺服器
- `templates/index.html` — 前端頁面，三種音樂來源共用同一套播放器邏輯：
  - 本機檔案：選檔後用 `URL.createObjectURL(file)` 產生本機 Blob URL；
    換一批新檔案時會 `URL.revokeObjectURL()` 釋放舊的，避免分頁開久記憶體一直長
  - 登入 Google 帳號：勾選檔案後，`<audio>` 的 `src` 指向本站自己的
    `/api/drive/stream/<id>`（同源，不會有 CORS 或分享權限問題）
  - 雲端硬碟分享連結：從分享連結解析出檔案 ID，組成
    `https://drive.google.com/uc?export=download&id=FILE_ID` 直接當作
    `<audio>` 的 `src`，由瀏覽器直接向 Google 雲端硬碟串流播放
  - 音量／速度用 `<input type="range">` 綁定 `audio.volume` /
    `audio.playbackRate`（iOS 上 `volume` 會被系統忽略，改顯示提示文字）
- 關閉分頁或重新整理後，本機檔案的 Blob URL 會失效，需要重新選取；
  Google 帳號登入與雲端硬碟連結則不受影響

## 授權

個人專案，僅供自用。
