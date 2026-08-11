"""
app.py — MP3 網頁播放器
==========================
上傳 MP3（一次最多 5 首）→ 直接在網頁上播放，每首可獨立調整音量與播放速度。

路由：
  GET  /                          首頁（上傳 + 播放器）
  GET  /login  / POST /login      登入（僅設定 APP_PASSWORD 時啟用）
  GET  /logout
  POST /api/upload                上傳最多 5 首 MP3 → {job_id, tracks:[{name,filename,url}]}
  GET  /api/file/<job_id>/<fname> 串流播放單一 MP3（支援 Range 請求，可拖曳進度）
"""

from __future__ import annotations
import os
import uuid
from functools import wraps
from pathlib import Path

from flask import (Flask, request, jsonify, send_file,
                    render_template, session, redirect, url_for)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB，足夠 5 首 MP3
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

JOBS_DIR = Path(os.environ.get("JOBS_DIR", "/tmp/mp3_player_jobs"))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_AUDIO_EXT = {".mp3"}
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


# ── 輔助 ──────────────────────────────────────────────────────────────────────

def _job_dir(job_id: str) -> Path:
    p = JOBS_DIR / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_name(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in "._- ()[]（）【】")
    safe = safe.strip() or "file"
    return safe[:80]


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


@app.route("/api/upload", methods=["POST"])
@login_required
def upload():
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        return jsonify(error="未收到檔案"), 400
    if len(files) > MAX_FILES:
        return jsonify(error=f"一次最多上傳 {MAX_FILES} 首"), 400

    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_AUDIO_EXT:
            return jsonify(error=f"僅支援 .mp3 檔案：{f.filename}"), 400

    job_id = uuid.uuid4().hex
    out_dir = _job_dir(job_id)

    tracks = []
    used_names = set()
    for f in files:
        stem = _safe_name(Path(f.filename).stem)
        fname = stem + ".mp3"
        n = 1
        while fname in used_names or (out_dir / fname).exists():
            n += 1
            fname = f"{stem}_{n}.mp3"
        used_names.add(fname)
        f.save(str(out_dir / fname))
        tracks.append({
            "name": Path(f.filename).stem,
            "filename": fname,
            "url": url_for("stream_file", job_id=job_id, fname=fname),
        })

    return jsonify(job_id=job_id, tracks=tracks)


@app.route("/api/file/<job_id>/<fname>")
@login_required
def stream_file(job_id: str, fname: str):
    path = _job_dir(job_id) / fname
    if not path.exists():
        return jsonify(error="檔案不存在"), 404
    return send_file(str(path), mimetype="audio/mpeg", conditional=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5060))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
