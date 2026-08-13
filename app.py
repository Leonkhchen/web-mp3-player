"""
app.py — MP3 網頁播放器
==========================
上傳 MP3（一次最多 5 首）→ 直接在網頁上播放，每首可獨立調整音量與播放速度。

路由：
  GET  /                          首頁（上傳 + 播放器）
  GET  /login  / POST /login      登入（僅設定 APP_PASSWORD 時啟用）
  GET  /logout
  POST /api/upload                上傳最多 5 首 MP3（單檔 ≤ CHUNK_THRESHOLD）→ {job_id, tracks:[...]}
  POST /api/upload_chunk          分段上傳：接收單一分段
  POST /api/upload_chunk_finish   分段上傳：所有分段送完後合併成最終檔案 → {job_id, tracks:[...]}
  GET  /api/file/<job_id>/<fname> 串流播放單一 MP3（支援 Range 請求，可拖曳進度）

超過 100MB 的大檔案由前端自動切成多個小分段（chunk）依序上傳，避免手機行動網路
一次送出過大的請求容易逾時／中斷；所有分段到齊後由 /api/upload_chunk_finish 依序
合併回原始檔案。
"""

from __future__ import annotations
import os
import re
import shutil
import uuid
from functools import wraps
from pathlib import Path

from flask import (Flask, request, jsonify, send_file,
                    render_template, session, redirect, url_for)

app = Flask(__name__)
# 單一 HTTP 請求的大小上限。大檔案改走分段上傳，每段遠小於這個值，
# 所以這個上限主要是保護「不分段」的一般上傳與分段本身不要異常肥大。
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

JOBS_DIR = Path(os.environ.get("JOBS_DIR", "/tmp/mp3_player_jobs"))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_DIR = JOBS_DIR / "chunks"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_AUDIO_EXT = {".mp3"}
MAX_FILES = 5
# 分段上傳合併後的單一檔案大小上限（防止有人無限送分段把硬碟塞爆）
MAX_ASSEMBLED_SIZE = int(os.environ.get("MAX_UPLOAD_MB", "1024")) * 1024 * 1024
_UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{16,64}$")


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


def _unique_mp3_name(out_dir: Path, stem: str, used_names: set) -> str:
    stem = _safe_name(stem)
    fname = stem + ".mp3"
    n = 1
    while fname in used_names or (out_dir / fname).exists():
        n += 1
        fname = f"{stem}_{n}.mp3"
    used_names.add(fname)
    return fname


def _chunk_dir(upload_id: str) -> Path:
    p = CHUNK_DIR / upload_id
    p.mkdir(parents=True, exist_ok=True)
    return p


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
        fname = _unique_mp3_name(out_dir, Path(f.filename).stem, used_names)
        f.save(str(out_dir / fname))
        tracks.append({
            "name": Path(f.filename).stem,
            "filename": fname,
            "url": url_for("stream_file", job_id=job_id, fname=fname),
        })

    return jsonify(job_id=job_id, tracks=tracks)


# ── 分段上傳（大檔案）────────────────────────────────────────────────────────

@app.route("/api/upload_chunk", methods=["POST"])
@login_required
def upload_chunk():
    upload_id = request.form.get("upload_id", "")
    filename = request.form.get("filename", "")
    chunk = request.files.get("chunk")

    if not _UPLOAD_ID_RE.match(upload_id):
        return jsonify(error="upload_id 不合法"), 400
    if not filename or Path(filename).suffix.lower() not in ALLOWED_AUDIO_EXT:
        return jsonify(error="僅支援 .mp3 檔案"), 400
    if not chunk:
        return jsonify(error="缺少分段內容"), 400
    try:
        chunk_index = int(request.form.get("chunk_index", ""))
        total_chunks = int(request.form.get("total_chunks", ""))
    except ValueError:
        return jsonify(error="分段參數不合法"), 400
    if chunk_index < 0 or total_chunks <= 0 or chunk_index >= total_chunks:
        return jsonify(error="分段參數不合法"), 400

    d = _chunk_dir(upload_id)
    # 目前已收到的分段總大小 + 這段的大小，粗略防呆，避免無限塞爆硬碟
    existing_size = sum(p.stat().st_size for p in d.glob("*.part"))
    chunk.save(str(d / f"{chunk_index:06d}.part"))
    new_size = existing_size + (d / f"{chunk_index:06d}.part").stat().st_size
    if new_size > MAX_ASSEMBLED_SIZE:
        shutil.rmtree(d, ignore_errors=True)
        return jsonify(error=f"檔案超過大小上限（{MAX_ASSEMBLED_SIZE // 1024 // 1024}MB）"), 413

    return jsonify(ok=True, received=chunk_index)


@app.route("/api/upload_chunk_finish", methods=["POST"])
@login_required
def upload_chunk_finish():
    body = request.get_json(silent=True) or request.form
    upload_id = body.get("upload_id", "")
    filename = body.get("filename", "")
    try:
        total_chunks = int(body.get("total_chunks", ""))
    except (TypeError, ValueError):
        return jsonify(error="分段參數不合法"), 400

    if not _UPLOAD_ID_RE.match(upload_id):
        return jsonify(error="upload_id 不合法"), 400
    if not filename or Path(filename).suffix.lower() not in ALLOWED_AUDIO_EXT:
        return jsonify(error="僅支援 .mp3 檔案"), 400

    d = _chunk_dir(upload_id)
    parts = [d / f"{i:06d}.part" for i in range(total_chunks)]
    missing = [i for i, p in enumerate(parts) if not p.exists()]
    if missing:
        return jsonify(error=f"分段不齊全，缺少第 {missing} 段"), 400

    job_id = uuid.uuid4().hex
    out_dir = _job_dir(job_id)
    fname = _unique_mp3_name(out_dir, Path(filename).stem, set())
    dest = out_dir / fname

    try:
        with open(dest, "wb") as out:
            for p in parts:
                with open(p, "rb") as part_f:
                    shutil.copyfileobj(part_f, out)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    return jsonify(job_id=job_id, tracks=[{
        "name": Path(filename).stem,
        "filename": fname,
        "url": url_for("stream_file", job_id=job_id, fname=fname),
    }])


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
