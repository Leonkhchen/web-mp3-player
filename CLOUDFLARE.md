# Cloudflare 第一版：本機 MP3 播放器

部署目錄：`dist/`，無需 Python、Flask、Google OAuth 或資料庫。
保留原有 Zeabur 程式供第二版參考。

## 本機預覽

```sh
python -m http.server 5060 --directory dist
```

開啟 http://localhost:5060 。選取最多五首 MP3，支援播放暫停、前後曲、±20 秒、拖曳進度、每首獨立速度與音量設定。
音檔只在裝置內播放，重新整理後需重選。iOS 音量使用實體鍵；鎖屏、自動下一首與加入主畫面需在真實 iPhone 驗收。此版沒有 service worker，不保證離線重新開啟網站。

## Cloudflare 部署

Workers：在本機登入 Wrangler 後，於專案根目錄執行 `npx wrangler deploy`，設定已附於 wrangler.jsonc。
Pages：連結 GitHub，Framework 選 None，Build command 留空，Output directory 設 dist。
只部署 dist，不要部署 Flask 原始碼。此靜態版不包含原本 APP_PASSWORD 登入保護，如需要私人網站請另外設定 Cloudflare Access。

## 第二版

Google Drive 登入、檔案搜尋與串流改為 Workers API；以 OAuth state/PKCE 防護、伺服器端安全保存 token、到期更新與登出撤銷；串流需轉送 Range 並保留 206/Content-Range，不整檔載入記憶體。Google 分享連結不作為可靠串流主要路徑。
