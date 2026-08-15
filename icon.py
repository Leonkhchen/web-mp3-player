"""
icon.py — 產生網站圖示（PNG），純標準函式庫，不需要 Pillow 等額外套件。

用來給「加到主畫面 / 安裝 App」用的圖示：iOS 的 apple-touch-icon 只認
點陣圖（PNG），沒有現成美術圖檔的情況下，用簡單的漸層背景＋幾何形狀
畫出一個近似音符的圖案，跟網站本身「現正播放」畫面裡的專輯圖示同一套
配色（紫→粉漸層 + 白色圖形）。
"""

from __future__ import annotations
import struct
import zlib

# 跟 templates/index.html 裡 .disc 用的漸層色一致
_ACCENT = (124, 108, 255)     # #7c6cff
_ACCENT2 = (91, 108, 243)     # #5b6cf3
_PINK = (255, 139, 208)       # #ff8bd0


def _lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def _gradient_color(t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        u = t / 0.5
        c0, c1 = _ACCENT, _ACCENT2
    else:
        u = (t - 0.5) / 0.5
        c0, c1 = _ACCENT2, _PINK
    return (_lerp(c0[0], c1[0], u), _lerp(c0[1], c1[1], u), _lerp(c0[2], c1[2], u))


def _dist_to_segment(px, py, ax, ay, bx, by) -> float:
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby
    t = 0.0 if ab2 == 0 else max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    cx, cy = ax + abx * t, ay + aby * t
    dx, dy = px - cx, py - cy
    return (dx * dx + dy * dy) ** 0.5


def _make_pixels(size: int) -> bytes:
    """回傳 size x size 的 RGB pixel 資料（每列前面不含 filter byte，見 _to_png）。"""
    # 音符圖形的幾何參數（比例座標，0~1）
    head_cx, head_cy, head_r = 0.37, 0.66, 0.11
    stem_ax, stem_ay = 0.46, 0.60   # 音符頭右上緣，桿子起點
    stem_bx, stem_by = 0.66, 0.20   # 桿子頂端
    stem_w = 0.05
    flag_ax, flag_ay = stem_bx, stem_by
    flag_bx, flag_by = 0.82, 0.32
    flag_w = 0.09

    rows = []
    for y in range(size):
        row = bytearray()
        fy = y / size
        for x in range(size):
            fx = x / size
            t = (fx + fy) / 2  # 近似 135deg 漸層方向
            r, g, b = _gradient_color(t)

            # 音符頭（實心圓）
            dxh = (fx - head_cx) * size
            dyh = (fy - head_cy) * size
            in_head = (dxh * dxh + dyh * dyh) ** 0.5 <= head_r * size

            # 桿子（線段）
            d_stem = _dist_to_segment(
                fx * size, fy * size,
                stem_ax * size, stem_ay * size,
                stem_bx * size, stem_by * size,
            )
            in_stem = d_stem <= (stem_w * size) / 2

            # 旗標（線段，較粗，模擬八分音符的旗）
            d_flag = _dist_to_segment(
                fx * size, fy * size,
                flag_ax * size, flag_ay * size,
                flag_bx * size, flag_by * size,
            )
            in_flag = d_flag <= (flag_w * size) / 2

            if in_head or in_stem or in_flag:
                r, g, b = 255, 255, 255

            row += bytes((r, g, b))
        rows.append(bytes(row))
    return rows


def _to_png(rows: list[bytes], size: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit, color type 2 = RGB
    raw = bytearray()
    for row in rows:
        raw += b"\x00" + row  # filter type 0 (none) per scanline
    idat = zlib.compress(bytes(raw), 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


_cache: dict[int, bytes] = {}


def make_icon_png(size: int) -> bytes:
    """產生（並快取）指定邊長的正方形圖示 PNG bytes。"""
    if size not in _cache:
        _cache[size] = _to_png(_make_pixels(size), size)
    return _cache[size]
