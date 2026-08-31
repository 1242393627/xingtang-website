#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 WebP（q80 同尺寸 + 作品图 750w 变体）与 favicon"""
import os
from PIL import Image

DIR = r"C:/Users/Administrator/WorkBuddy/2026-08-11-15-25-22/assets/images"
ROOT = r"C:/Users/Administrator/WorkBuddy/2026-08-11-15-25-22"

def to_webp(path, out, max_w=None, quality=80):
    img = Image.open(path)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    if max_w and img.width > max_w:
        r = max_w / img.width
        img = img.resize((max_w, int(img.height * r)), Image.LANCZOS)
    img.save(out, "WEBP", quality=quality, method=6)
    return os.path.getsize(out)

# 1. 全部 jpg -> 同尺寸 webp
count = 0
for f in sorted(os.listdir(DIR)):
    if not f.lower().endswith((".jpg", ".jpeg")):
        continue
    name = os.path.splitext(f)[0]
    jp = os.path.join(DIR, f)
    wp = os.path.join(DIR, name + ".webp")
    if os.path.exists(wp) and os.path.getsize(wp) < os.path.getsize(jp):
        continue
    sz = to_webp(jp, wp)
    print(f"webp  {f:22s} -> {name}.webp {sz//1024}KB")
    count += 1

# 2. 作品图 work_01~08 生成 750w 变体
for i in range(1, 9):
    name = f"work_{i:02d}"
    jp = os.path.join(DIR, name + ".jpg")
    out = os.path.join(DIR, name + "-750.webp")
    if not os.path.exists(jp):
        continue
    im = Image.open(jp)
    if im.width <= 750:
        continue
    sz = to_webp(jp, out, max_w=750)
    print(f"750w   {name}.jpg -> {name}-750.webp {sz//1024}KB")

# 3. favicon.ico + apple-touch-icon.png
logo = Image.open(os.path.join(DIR, "logo.png")).convert("RGBA")
logo32 = logo.resize((32, 32), Image.LANCZOS)
logo32.save(os.path.join(ROOT, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32)])
apple = logo.resize((180, 180), Image.LANCZOS)
apple.save(os.path.join(ROOT, "apple-touch-icon.png"))
print("favicon.ico + apple-touch-icon.png 已生成")
print("DONE")
