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
CMD ["sh", "-c", "gunicorn -w 1 --threads 4 -b 0.0.0.0:${PORT:-5060} app:app"]
