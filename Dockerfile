FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5060
EXPOSE 5060

# 用 gunicorn 而不是 Flask 內建的開發用伺服器（該 dev server 官方就註明
# 不建議用在正式環境）。頁面本身很輕量（沒有檔案上傳/串流），維持
# 保守的預設值即可。
CMD ["sh", "-c", "gunicorn -w 2 --threads 4 -b 0.0.0.0:${PORT:-5060} app:app"]
