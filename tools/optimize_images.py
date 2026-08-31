#!/usr/bin/env python3
"""
星棠官网 · 图片优化工具
遍历 assets/images/ 下的 JPG，转换为 WebP 并压缩到 ≤100KB
依赖: pip install Pillow
"""
import os
from PIL import Image

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images")
total_before = 0
total_after = 0
converted = 0

for fname in sorted(os.listdir(SRC)):
    if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
    path = os.path.join(SRC, fname)
    size_before = os.path.getsize(path)
    total_before += size_before
    
    # 转 WebP
    img = Image.open(path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGBA')
    else:
        img = img.convert('RGB')
    
    webp_name = fname.rsplit('.', 1)[0] + '.webp'
    webp_path = os.path.join(SRC, webp_name)
    
    # 压缩到 100KB 以内
    quality = 75
    img.save(webp_path, 'WEBP', quality=quality)
    while os.path.getsize(webp_path) > 100 * 1024 and quality > 10:
        quality -= 5
        img.save(webp_path, 'WEBP', quality=quality)
    
    size_after = os.path.getsize(webp_path)
    total_after += size_after
    converted += 1
    
    print(f"  {fname}: {size_before//1024}KB → {webp_name}: {size_after//1024}KB (q={quality})")

print(f"\n总计: {converted} 张, {total_before//1024}KB → {total_after//1024}KB, 节省 {100-total_after*100//total_before}%")
