# 星棠官网（XingTang Website）

> 营销展示型美业培训学校官网 —— **零框架**实现：原生 HTML/CSS/JS 前端 + Python 标准库手写 CMS 后端，无任何 npm/pip 重依赖， clone 下来即可跑。

**线上示例**：https://shop.ywye.top/

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Framework-Zero-orange.svg)](#)

---

## ✨ 特性

- **零框架**：前端无 Vue/React，后端仅用 Python 标准库 `http.server` 手写 API，克隆即用
- **CMS 后台**：登录 / 课程 / 资讯 / 轮播 / 城市 / 留资管理，图片上传，Word(.docx) 一键导入正文
- **资讯 SSR**：文章详情页服务端渲染完整 HTML（含 JSON-LD），搜索引擎与 AI 引擎（豆包/头条/百度）无需执行 JS 即可抓取全文
- **SEO/GEO 深度优化**：唯一 H1、6 类结构化数据（Organization / WebSite / ItemList / FAQPage / NewsArticle / BreadcrumbList）、头条 bytedance 时间标签、ttzz 自动推送、百度/字节验证文件
- **动态 sitemap**：CMS 实时生成 `/sitemap.xml`，发布文章自动更新 lastmod，零维护
- **性能**：全量 WebP（`image-set()` + `<picture>` 双格式回退）、gzip、脚本 defer、图片 ≤100KB
- **安全**：HSTS / CSP / X-Frame-Options 等 6 项安全头、后台双层认证（basic auth + token）、表单频控 + 一次性 token 防重放、IP 直连 301 收敛
- **双存储**：MySQL(MariaDB) 为主 + JSON 文件镜像兜底，MySQL 宕机自动降级，数据双保险

## 🧰 技术栈

| 层 | 技术 |
|---|---|
| 前端 | 原生 HTML/CSS/JS、Swiper 11（CDN）、IntersectionObserver 动画 |
| 后端 | Python 3.8+ 标准库 `http.server`（零框架，单文件） |
| 数据库 | MySQL / MariaDB（pymysql，可选；无 MySQL 自动降级 JSON 存储） |
| Web 服务 | Nginx（反代 + 静态 + 安全头） |
| 进程管理 | systemd（`tools/cms_server.service`） |

## 🚀 快速开始（本地）

```bash
git clone https://github.com/1242393627/xingtang-website.git
cd xingtang-website
python3 cms_server.py
# 打开 http://127.0.0.1:8081/   后台: http://127.0.0.1:8081/admin/
```

> 本地无 MySQL 时自动使用 `content/*.json` 文件存储，无需任何配置。
> 可选安装 `pip install pymysql` 启用 MySQL。

**后台默认账号**：`admin` / `Xingtang@2026` —— ⚠️ 首次登录后请立即在后台修改密码。

## 🖥️ 生产部署（Ubuntu + Nginx + MariaDB）

完整手册见 [MIGRATION.md](MIGRATION.md)（含资产清单、逐步命令、验证清单、回滚预案）。核心步骤：

### 1. 环境准备

```bash
apt install -y nginx mariadb-server python3
pip3 install pymysql
```

### 2. 放置站点

```bash
mkdir -p /www/server/nginx/html/article
cp -r . /www/server/nginx/html/article/   # 或 git clone
```

### 3. 初始化 MySQL（可选，推荐）

```bash
# 修改 tools/init_mysql.py 顶部的连接信息后执行
python3 tools/init_mysql.py          # 建库 xingtang_cms + 6 张表 + 专用账号
python3 tools/migrate_json_to_mysql.py   # 把 content/*.json 导入 MySQL
```

CMS 通过 web root 外的 JSON 文件读取连接信息（路径见 `cms_server.py` 顶部常量，可自行调整）：

```json
// /www/server/nginx/.xingtang_mysql.json（chmod 600）
{"host": "127.0.0.1", "port": 3306, "root_password": "...", "cms_db": "xingtang_cms", "cms_user": "xingtang_cms", "cms_password": "..."}
```

### 4. Nginx 站点配置

```bash
cp nginx-cms.conf /etc/nginx/conf.d/your-site.conf
# 修改其中的 server_name、证书路径、YOUR_SERVER_IP 后：
nginx -t && nginx -s reload
```

> ⚠️ `/admin/` 使用 basic auth，需生成密码文件：
> ```bash
> htpasswd -c /www/server/nginx/.htpasswd_xingtang youradmin
> chown root:www /www/server/nginx/.htpasswd_xingtang && chmod 640 /www/server/nginx/.htpasswd_xingtang
> ```
> （文件属组必须是 nginx worker 用户，否则登录时 500）

### 5. systemd 自启

```bash
cp tools/cms_server.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now cms_server
```

### 6. 验证

```bash
curl -skI https://your-domain/          # 200 + 6 项安全头
curl -sk https://your-domain/api/public # JSON 数据
curl -sk https://your-domain/sitemap.xml# 动态 sitemap
curl -sk -o /dev/null -w "%{http_code}" https://your-domain/admin/   # 401（待认证）
```

## 🔑 后台

| 层 | 说明 |
|---|---|
| Nginx basic auth | 浏览器弹窗认证（保护后台页面本身） |
| CMS 应用登录 | `admin` / 初始密码见 `cms_server.py` 的 `DEFAULT_PASS`，**上线后立即修改** |

功能：课程/资讯/轮播/城市/留资 CRUD、图片上传（魔数校验）、Word 导入、批量删除、操作日志、修改密码。

## 📁 目录结构

```
├── index.html            # 首页（单页，静态内容兜底 + CMS 数据增强）
├── cms_server.py         # 后端单文件：API + SSR + 上传 + Word 导入
├── admin/                # 管理后台（SPA）
├── assets/               # css / js / images（webp 优先 + jpg 回退）
├── content/              # CMS 数据（JSON；MySQL 为主存储时作镜像兜底）
├── tools/                # 运维：图片压缩 / WebP 生成 / MySQL 迁移 / 一键备份 / systemd
├── deploy.sh             # 一键部署（scp 全量 + 重启 CMS）
├── nginx-cms.conf        # Nginx vhost 模板（安全头 / gzip / IP 301 / 双层认证 / 反代）
├── MIGRATION.md          # 完整迁移手册
└── overview.md           # SEO/GEO 与安全审计整改记录
```

## 🔒 安全说明

- 所有凭据（MySQL / 微信 JS-SDK / 后台密码）存放于 **web root 之外**的 JSON 文件（`chmod 600`），仓库内不含任何密钥
- 微信 JS-SDK 配置：在服务器上创建 `wx.json`（含 `appid` / `appsecret`），路径见 `cms_server.py` 的 `WX_CONFIG_FILE`
- 表单接口内置：手机号格式校验、同 IP/同手机号每日频控、一次性 token 防重放
- `/api/*` 数据接口除登录与公开聚合外一律要求 token

## 📄 License

[MIT](LICENSE)
