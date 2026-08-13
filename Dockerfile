FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5060
EXPOSE 5060

# 用 gunicorn 而不是 Flask 內建的開發用伺服器：
# Flask 自帶的 dev server 不是設計給正式環境用的，串流大型 mp3 檔案時
# （尤其是行動網路、速度較慢、需要維持連線較久）容易不穩定。
# --timeout 拉長是因為串流大檔案給網路較慢的手機時，單一 worker 忙著
# 傳輸資料的時間可能比預設的 30 秒還久。
CMD ["sh", "-c", "gunicorn -w 2 --threads 4 --timeout 300 -b 0.0.0.0:${PORT:-5060} app:app"]
