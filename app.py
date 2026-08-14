"""
app.py — MP3 網頁播放器
==========================
選取手機/電腦上的 MP3（一次最多 5 首）→ 直接在瀏覽器裡播放，每首可獨立
調整音量與播放速度。

檔案完全不會上傳到伺服器：選取後用瀏覽器內建的
`URL.createObjectURL()` 直接在本機播放，音檔資料從頭到尾只留在使用者
的裝置上。伺服器只負責回應這個靜態頁面（以及可選的密碼保護）。

路由：
  GET  /                首頁（選檔 + 播放器，邏輯都在前端 JS）
  GET  /login  / POST /login  登入（僅設定 APP_PASSWORD 時啟用）
  GET  /logout
"""

from __future__ import annotations
import os
from functools import wraps

from flask import Flask, request, render_template, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
MAX_FILES = 5


# ── 密碼保護 ──────────────────────────────────────────────────────────────────

def _check_auth():
    if not APP_PASSWORD:
        return True
    return session.get("authed") is True


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _check_auth():
            if request.path.startswith("/api/"):
                return jsonify(error="未授權"), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET"])
def login_page():
    if _check_auth():
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    pwd = request.form.get("password", "")
    if pwd == APP_PASSWORD:
        session["authed"] = True
        return redirect(url_for("index"))
    return render_template("login.html", error="密碼錯誤"), 401


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page") if APP_PASSWORD else url_for("index"))


@app.after_request
def _no_cache_html(resp):
    # 頁面邏輯全部內嵌在 HTML 裡，手機瀏覽器（尤其 iOS Safari）常會快取
    # 整頁 HTML，導致改版後手機還在跑舊版程式碼，所以 HTML 一律關閉快取。
    if resp.content_type and resp.content_type.startswith("text/html"):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
    return resp


# ═══════════════════════════════════════════════════════════════════════════════
#  路由
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return render_template(
        "index.html",
        has_password=bool(APP_PASSWORD),
        max_files=MAX_FILES,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5060))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
