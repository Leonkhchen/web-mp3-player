"""
app.py — MP3 網頁播放器
==========================
選取手機/電腦上的 MP3（一次最多 5 首）→ 直接在瀏覽器裡播放，每首可獨立
調整音量與播放速度。音樂來源有三種：

  1. 本機檔案 —— 完全不上傳，瀏覽器用 URL.createObjectURL() 本機播放
  2. Google 雲端硬碟分享連結 —— 貼上「知道連結的使用者可檢視」的連結，
     瀏覽器直接向 drive.google.com 串流播放
  3. 登入自己的 Google 帳號 —— OAuth 授權後，從自己 Drive 裡選檔案播放，
     不需要先把檔案設成公開分享；播放時由本伺服器代理向 Drive API 要資料
     （帶使用者的 access token），前端只是打自己網站的同源 URL

路由：
  GET  /                            首頁
  GET  /login  / POST /login        登入（僅設定 APP_PASSWORD 時啟用）
  GET  /logout
  GET  /auth/google/login           導去 Google 的 OAuth 同意畫面
  GET  /auth/google/callback        OAuth 導回來，交換 token
  GET  /auth/google/logout          登出 Google（只清掉存在本伺服器的 token）
  GET  /api/drive/status            目前是否已連接 Google
  GET  /api/drive/list              列出使用者 Drive 裡的 mp3（可用 q 搜尋檔名）
  GET  /api/drive/stream/<file_id>  代理 Drive API 把檔案內容串流回來（支援 Range）
"""

from __future__ import annotations
import os
import re
import secrets
import time
from functools import wraps

import requests
from flask import (Flask, Response, jsonify, redirect, render_template,
                    request, session, stream_with_context, url_for)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
MAX_FILES = 5

# ── Google OAuth 設定 ──────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
# 唯讀權限：只能看檔案內容，不能新增/修改/刪除
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

_DRIVE_FILE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{10,100}$")

# token 存在伺服器記憶體裡（不放進瀏覽器 cookie，避免外洩），
# 用一個隨機 id（存在 session cookie 裡）當 key 對應回來。
# 伺服器重啟後這裡會清空，使用者只需要重新登入一次 Google。
_google_tokens: dict[str, dict] = {}


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
    _google_tokens.pop(session.get("gsid", ""), None)
    session.clear()
    return redirect(url_for("login_page") if APP_PASSWORD else url_for("index"))


@app.after_request
def _no_cache_html(resp):
    # 頁面邏輯全部內嵌在 HTML 裡，手機瀏覽器（尤其 iOS Safari）常會快取
    # 整頁 HTML，導致改版後手機還在跑舊版程式碼，所以 HTML 一律關閉快取。
    if resp.content_type and resp.content_type.startswith("text/html"):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
    return resp


# ── Google OAuth 輔助 ──────────────────────────────────────────────────────

def _get_valid_access_token() -> str | None:
    """回傳目前 session 對應的有效 access token；過期就用 refresh token 換新的；
    完全沒登入或換不到就回 None。"""
    gsid = session.get("gsid")
    tok = _google_tokens.get(gsid) if gsid else None
    if not tok:
        return None

    if time.time() < tok["expires_at"] - 60:
        return tok["access_token"]

    refresh_token = tok.get("refresh_token")
    if not refresh_token:
        return None

    try:
        r = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return None

    tok["access_token"] = data["access_token"]
    tok["expires_at"] = time.time() + data.get("expires_in", 3600)
    return tok["access_token"]


@app.route("/auth/google/login")
@login_required
def google_login():
    if not GOOGLE_CONFIGURED:
        return jsonify(error="伺服器尚未設定 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET"), 500

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": url_for("google_callback", _external=True),
        "response_type": "code",
        "scope": DRIVE_SCOPE,
        "access_type": "offline",
        "prompt": "consent select_account",
        "state": state,
    }
    qs = "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
    return redirect(f"{GOOGLE_AUTH_URL}?{qs}")


@app.route("/auth/google/callback")
@login_required
def google_callback():
    error = request.args.get("error")
    if error:
        return redirect(url_for("index", drive_error=error))

    state = request.args.get("state", "")
    if not state or state != session.get("oauth_state"):
        return redirect(url_for("index", drive_error="state_mismatch"))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("index", drive_error="no_code"))

    try:
        r = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url_for("google_callback", _external=True),
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return redirect(url_for("index", drive_error="token_exchange_failed"))

    gsid = session.get("gsid") or secrets.token_urlsafe(16)
    session["gsid"] = gsid
    existing = _google_tokens.get(gsid, {})
    _google_tokens[gsid] = {
        "access_token": data["access_token"],
        # 第二次之後同意可能不會再給 refresh_token，沿用舊的
        "refresh_token": data.get("refresh_token") or existing.get("refresh_token"),
        "expires_at": time.time() + data.get("expires_in", 3600),
    }
    return redirect(url_for("index"))


@app.route("/auth/google/logout")
@login_required
def google_logout():
    gsid = session.pop("gsid", None)
    if gsid:
        _google_tokens.pop(gsid, None)
    return redirect(url_for("index"))


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
        google_configured=GOOGLE_CONFIGURED,
    )


@app.route("/api/drive/status")
@login_required
def drive_status():
    return jsonify(connected=_get_valid_access_token() is not None, configured=GOOGLE_CONFIGURED)


@app.route("/api/drive/list")
@login_required
def drive_list():
    token = _get_valid_access_token()
    if not token:
        return jsonify(error="尚未連接 Google 帳號"), 401

    q_text = request.args.get("q", "").strip()
    q = "trashed=false and (mimeType='audio/mpeg' or name contains '.mp3')"
    if q_text:
        safe = q_text.replace("\\", "\\\\").replace("'", "\\'")
        q += f" and name contains '{safe}'"

    try:
        r = requests.get(f"{DRIVE_API}/files", headers={
            "Authorization": f"Bearer {token}",
        }, params={
            "q": q,
            "fields": "files(id,name,size)",
            "pageSize": 30,
            "orderBy": "name",
            "spaces": "drive",
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        return jsonify(error=f"讀取雲端硬碟清單失敗：{e}"), 502

    return jsonify(files=data.get("files", []))


@app.route("/api/drive/stream/<file_id>")
@login_required
def drive_stream(file_id: str):
    if not _DRIVE_FILE_ID_RE.match(file_id):
        return jsonify(error="檔案 ID 不合法"), 400

    token = _get_valid_access_token()
    if not token:
        return jsonify(error="尚未連接 Google 帳號"), 401

    headers = {"Authorization": f"Bearer {token}"}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        upstream = requests.get(
            f"{DRIVE_API}/files/{file_id}",
            headers=headers,
            params={"alt": "media"},
            stream=True,
            timeout=30,
        )
    except requests.RequestException:
        return jsonify(error="連線到 Google 雲端硬碟失敗"), 502

    if upstream.status_code in (401, 403):
        return jsonify(error="沒有權限存取這個檔案，或登入已過期"), upstream.status_code
    if upstream.status_code == 404:
        return jsonify(error="找不到這個檔案"), 404
    if upstream.status_code not in (200, 206):
        return jsonify(error=f"Google 雲端硬碟回應異常（HTTP {upstream.status_code}）"), 502

    passthrough_headers = {}
    for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
        if h in upstream.headers:
            passthrough_headers[h] = upstream.headers[h]
    passthrough_headers.setdefault("Accept-Ranges", "bytes")
    passthrough_headers.setdefault("Content-Type", "audio/mpeg")

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(
        stream_with_context(generate()),
        status=upstream.status_code,
        headers=passthrough_headers,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5060))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
