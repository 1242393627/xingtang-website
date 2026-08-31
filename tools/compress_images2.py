#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮：非 Hero 图缩到最长边1280 + 质量下限38，硬性压到目标体积"""
import os, io
from PIL import Image

DIR = r"C:/Users/Administrator/WorkBuddy/2026-08-11-15-25-22/assets/images"
HERO = {"work_09.jpg","work_10.jpg","work_11.jpg","work_12.jpg"}
TARGET = {**{f: 180*1024 for f in HERO}, **{"og-image.jpg": 200*1024}}

def compress(path, target_bytes, max_edge):
    img = Image.open(path)
    if img.mode in ("RGBA","P","LA"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255,255,255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    w, h = img.size
    cur_edge = max(w, h)
    # 逐级缩小分辨率直到达标
    while True:
        if cur_edge > max_edge:
            r = max_edge / cur_edge
            img = img.resize((max(1,int(w*r)), max(1,int(h*r))), Image.LANCZOS)
        best = None
        for q in range(82, 37, -2):
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
            if buf.tell() <= target_bytes:
                best = (q, buf.tell(), img.size)
                break
        if best:
            q, size, dim = best
            with open(path, "wb") as f:
                f.write(buf.getvalue())
            return q, size, dim
        # 缩小分辨率再试
        max_edge = int(max_edge * 0.85)
        cur_edge = max(img.size)
        if max_edge < 640:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=45, optimize=True, progressive=True)
            with open(path, "wb") as f:
                f.write(buf.getvalue())
            return 45, buf.tell(), img.size

total_before = total_after = 0
for name in sorted(os.listdir(DIR)):
    if not name.lower().endswith((".jpg",".jpeg")):
        continue
    p = os.path.join(DIR, name)
    before = os.path.getsize(p)
    total_before += before
    target = TARGET.get(name, 100*1024)
    if before <= target:
        total_after += before
        continue
    q, after, dim = compress(p, target, 1600 if name in HERO else 1280)
    total_after += after
    flag = "OK " if after <= target else "WARN"
    print(f"{name:24s} {flag} {before/1024:7.1f}KB -> {after/1024:7.1f}KB (q={q} {dim[0]}x{dim[1]})")

print(f"\nTOTAL: {total_before/1048576:.2f}MB -> {total_after/1048576:.2f}MB (省 {100*(1-total_after/total_before):.1f}%)")
