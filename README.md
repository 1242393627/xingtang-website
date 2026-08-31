# 星棠化妆培训学校 · 官网

> 线上地址：https://shop.ywye.top/
> 技术栈：零框架 —— 原生 HTML/CSS/JS + Swiper 11（CDN）+ Python 标准库 `http.server` 手写 CMS API + MySQL(MariaDB) 主存储 / JSON 镜像兜底 + Nginx

## 目录结构

```
├── index.html          # 官网首页（单页）
├── cms_server.py       # CMS 后端（:8081，SSR 资讯页 / API / 上传 / Word 导入）
├── admin/index.html    # 管理后台（basic auth + token 双层）
├── assets/             # css / js / images（webp 优先 + jpg 回退）
├── content/            # CMS 数据（JSON 镜像；MySQL 为主存储）
│   ├── courses/ news/ banners/ cities/ settings/
│   ├── leads/          # 招生线索（git 中仅占位，真实数据在服务器）
│   └── uploads/        # 后台上传图片（同上）
├── tools/              # 运维工具（图片压缩 / WebP 生成 / MySQL 迁移 / 备份）
├── deploy.sh           # 一键部署脚本（scp + 重启 CMS）
├── nginx-cms.conf      # Nginx vhost（安全头 / gzip / IP 301 / auth / 反代）
├── MIGRATION.md        # 完整迁移手册
├── overview.md         # SEO/GEO + 安全审计整改记录
└── robots.txt / sitemap.xml（sitemap 由 CMS 动态生成）
```

## 特性

- **SEO/GEO**：唯一 H1、六类 JSON-LD（Organization/WebSite/ItemList/FAQPage/NewsArticle/BreadcrumbList）、bytedance 时间标签、动态 sitemap、头条 ttzz 自动推送
- **性能**：全量 WebP + `image-set()`/`<picture>`、gzip、defer、图片 ≤100KB（Hero ≤180KB）
- **安全**：HSTS/CSP/XFO 等 6 项安全头、admin 双层认证、表单频控+一次性 token、IP 直连 301 收敛
- **运维**：systemd 自启（`tools/cms_server.service`）、一键迁移备份（`tools/migrate_backup.sh`）

## 部署 / 迁移

见 `MIGRATION.md`（含资产清单、7 步恢复流程、验证清单、回滚预案）。

## 安全说明

- 所有凭据存于服务器 web root 外（`/www/server/nginx/.xingtang_*`），**不入库**
- `MIGRATION.md` / `overview.md` 中的密码已脱敏为占位符
- 线索数据（leads）只存在服务器，仓库内仅目录占位
