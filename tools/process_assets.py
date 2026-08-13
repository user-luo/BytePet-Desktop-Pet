# -*- coding: utf-8 -*-
"""素材处理：将 cat/ 下原始猫图抠图去背景，裁剪到内容边界，保存为透明 PNG。

对应需求「图片转换的时候保留猫猫关键细节，保留特别之处」：
    - rembg (u2net) 保留猫的毛发 / 眼睛 / 爪子等细节，仅移除背景
    - 自动裁掉多余透明边距，得到紧凑素材
    - 顺便生成程序图标 icon.ico

用法：  python tools/process_assets.py
"""
import io
import os
import sys
import time

# Windows 控制台默认 GBK，避免输出符号 / emoji 时崩溃
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from PIL import Image  # noqa: E402

SRC_DIR = os.path.join(_ROOT, "cat")
DST_DIR = os.path.join(_ROOT, "assets", "pet")
ASSETS_DIR = os.path.join(_ROOT, "assets")
MAX_SIDE = 1024


def cutout(src_path: str, dst_path: str):
    from rembg import remove
    im = Image.open(src_path).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    out = remove(buf.getvalue())
    res = Image.open(io.BytesIO(out)).convert("RGBA")
    bbox = res.getbbox()
    if bbox:
        res = res.crop(bbox)
    res.save(dst_path)
    a = res.split()[-1]
    hist = a.histogram()
    transparent = hist[0]
    total = res.size[0] * res.size[1]
    return res.size[0], res.size[1], (transparent / total if total else 0)


def make_icon(src_png: str, ico_path: str):
    im = Image.open(src_png).convert("RGBA")
    w, h = im.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    canvas.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64),
                                  (48, 48), (32, 32), (16, 16)])


def main():
    os.makedirs(DST_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith(".png"))
    print(f"共 {len(files)} 张原图待处理", flush=True)
    results = []
    t_all = time.time()
    for f in files:
        src = os.path.join(SRC_DIR, f)
        dst = os.path.join(DST_DIR, f)
        t0 = time.time()
        try:
            w, h, ratio = cutout(src, dst)
            dt = time.time() - t0
            print(f"  [OK] {f} -> {w}x{h} transparent={ratio:.1%}  {dt:.1f}s", flush=True)
            results.append((f, dst, ratio))
        except Exception as e:
            print(f"  [FAIL] {f}: {e}", flush=True)
    if results:
        try:
            make_icon(results[0][1], os.path.join(ASSETS_DIR, "icon.ico"))
            print(f"icon.ico generated from {results[0][0]}", flush=True)
        except Exception as e:
            print(f"icon failed: {e}", flush=True)
    print(f"ALL DONE in {time.time() - t_all:.1f}s", flush=True)


if __name__ == "__main__":
    main()
