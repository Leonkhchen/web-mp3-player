# 🎧 MP3 網頁播放器

上傳 MP3 檔案（一次最多 5 首），直接在網頁上播放，每首歌曲都可以獨立調整
**音量** 與 **播放速度**，不需要轉檔，也不需要任何外部 API。

## 功能

- 拖放或選擇上傳，一次最多 5 首 `.mp3`
- 每首歌曲有自己的播放器，可獨立調整：
  - 🔊 音量（0% ～ 100%）
  - ⏩ 播放速度（0.5x ～ 2x）
- 串流播放支援 Range 請求，可自由拖曳播放進度
- 可選密碼保護（設定 `APP_PASSWORD` 環境變數後啟用登入頁）
- 超過 100MB 的檔案會自動切成 8MB 一段依序上傳（分段失敗會自動重試一次），
  合併後單一檔案上限為 `MAX_UPLOAD_MB`（預設 1024MB）

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
| `JOBS_DIR`      | 上傳檔案暫存路徑                       | `/tmp/mp3_player_jobs`   |
| `APP_PASSWORD`  | 設定後開啟登入頁保護整個網站           | 無（不啟用）             |
| `SECRET_KEY`    | Flask session 加密金鑰                 | 隨機產生                 |
| `MAX_UPLOAD_MB` | 分段上傳合併後的單一檔案大小上限（MB） | `1024`                    |

## 用 Docker 執行

```bash
docker build -t mp3-web-player .
docker run -p 5060:5060 mp3-web-player
```

## 架構筆記

- `app.py` — Flask 主程式：可選的密碼保護、上傳驗證（副檔名 `.mp3`、數量上限 5）、
  以 `send_file(..., conditional=True)` 串流音檔（支援 Range 請求）；
  另有 `/api/upload_chunk` + `/api/upload_chunk_finish` 處理大檔案分段上傳與合併
- `templates/index.html` — 前端頁面，單一 `Audio` 物件驅動所有播放邏輯，音量／速度
  用 `<input type="range">` 綁定 `audio.volume` / `audio.playbackRate`（iOS 上 `volume`
  會被系統忽略，改顯示提示文字），無外部套件依賴；> 100MB 的檔案改用
  `File.slice()` 切成小段個別以 `XMLHttpRequest` 上傳，逐段有逾時與重試
- 上傳的檔案暫存在 `JOBS_DIR` 指定的路徑下，以隨機 job id 分隔，僅為暫存用途；
  分段上傳過程中的暫存分段存在 `JOBS_DIR/chunks/`，合併完成或失敗都會清除

## 授權

個人專案，僅供自用。
