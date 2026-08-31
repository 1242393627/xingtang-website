#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星棠官网图片就地压缩：Hero 保真 ≤180KB、og ≤200KB、其余 ≤100KB"""
import os, io, sys
from PIL import Image

DIR = r"C:/Users/Administrator/WorkBuddy/2026-08-11-15-25-22/assets/images"
HERO = {"work_09.jpg","work_10.jpg","work_11.jpg","work_12.jpg"}
OG = {"og-image.jpg"}
TARGET = {**{f: 180*1024 for f in HERO}, **{f: 200*1024 for f in OG}}
MAX_EDGE = 1600

def compress(path, target_bytes):
    img = Image.open(path)
    if img.mode in ("RGBA","P","LA"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255,255,255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_EDGE:
        ratio = MAX_EDGE / max(w, h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
    for q in range(84, 49, -3):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= target_bytes or q <= 52:
            with open(path, "wb") as f:
                f.write(buf.getvalue())
            return q, buf.tell()
    return q, buf.tell()

total_before = total_after = 0
for name in sorted(os.listdir(DIR)):
    if not name.lower().endswith((".jpg",".jpeg")):
        continue
    p = os.path.join(DIR, name)
    before = os.path.getsize(p)
    total_before += before
    target = TARGET.get(name, 100*1024)
    if before <= target:
        print(f"{name:24s} skip  {before/1024:7.1f}KB")
        total_after += before
        continue
    q, after = compress(p, target)
    total_after += after
    flag = "OK " if after <= target else "WARN"
    print(f"{name:24s} {flag} {before/1024:7.1f}KB -> {after/1024:7.1f}KB  (q={q})")

print(f"\nTOTAL: {total_before/1048576:.2f}MB -> {total_after/1048576:.2f}MB  (省 {100*(1-total_after/total_before):.1f}%)")
