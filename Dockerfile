FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5060
EXPOSE 5060

# 用 gunicorn 而不是 Flask 內建的開發用伺服器（該 dev server 官方就註明
# 不建議用在正式環境）。
#
# --workers 一定要是 1：Google OAuth token 是存在 app.py 裡的一個
# process 記憶體字典（_google_tokens），如果開多個 worker process，
# 每個 process 記憶體是分開的，登入後拿到的 token 只會存在處理該次
# callback 請求的那個 worker 裡，下一次請求被路由到另一個 worker 時
# 就會找不到 token、變成一直被要求重新登入。維持單一 worker + 多執行緒
# 才能確保所有請求共用同一份記憶體。
#
# --worker-class gthread 一定要加：光寫 --threads 對預設的 sync worker
# 沒有作用（會被忽略），要指定 gthread 這個 worker 類型 --threads 才會
# 真的生效，不然同時間只能處理一個請求，串流 Google 雲端硬碟大檔案時
# 會擋住其他請求。--timeout 拉長是因為串流較大的檔案、或 Google Drive
# API 回應較慢時，可能會超過 gunicorn 預設的 30 秒逾時而被中斷連線。
CMD ["sh", "-c", "gunicorn -w 1 --worker-class gthread --threads 4 --timeout 300 -b 0.0.0.0:${PORT:-5060} app:app"]
