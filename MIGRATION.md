# 星棠官网 · 完整迁移手册（shop.ywye.top）

> 迁移可行性：**完全可行，免重构**。全部资产已清单化：代码+静态文件（rsync 打包）、数据（MySQL dump + JSON 镜像双保险）、凭据（5 个文件）、nginx 配置（nginx-cms.conf 现成）。预计 0.5~1 个工作日（含 DNS/CDN 生效等待）。

---

## 一、资产清单（源服务器）

| 类别 | 位置 | 说明 |
|---|---|---|
| 站点文件 | `/www/server/nginx/html/article/`（约 52MB） | index.html、assets/、admin/、cms_server.py、content/（JSON 镜像 + uploads） |
| 数据库 | MariaDB 库 `xingtang_cms`（6 表） | **主存储**；content/*.json 为镜像兜底，双保险 |
| 凭据① | `/www/server/nginx/.xingtang_mysql.json`（600） | MySQL 连接（库/用户/密码） |
| 凭据② | `/www/server/nginx/.xingtang_passwd` | 后台登录密码（对应 ADMIN_USER=admin） |
| 凭据③ | `/www/server/nginx/.xingtang_wx.json`（600） | 微信 JS-SDK 凭据 |
| 凭据④ | `/www/server/nginx/.htpasswd_xingtang`（600） | /admin/ basic auth（xtadmin / <basic-auth-密码-见服务器/.htpasswd_xingtang>） |
| 日志 | `/www/server/nginx/.xingtang_logs/` | CMS 操作日志 |
| nginx | `/www/server/panel/vhost/nginx/shop.ywye.top.conf` | 安全头/gzip/auth_basic/www 301/反代（本地副本：`nginx-cms.conf`） |
| SSL | `/etc/tencent-ssl/shop.ywye.top/{fullchain,privkey}.pem` | 域名证书，不绑定 IP；**私钥不随包传输** |
| 进程 | `python3 cms_server.py` :8081 | **已配置 systemd 自启**（cms_server.service） |
| 外部 | 域名 DNS → YOUR_SERVER_IP；腾讯云 CDN 回源 | 迁移后需切换 |

---

## 二、源服务器：一键备份

```bash
scp tools/migrate_backup.sh tools/cms_server.service root@<源IP>:/root/
ssh root@<源IP> "bash /root/migrate_backup.sh"
# 产出 /root/xingtang_migrate_<时间戳>.tar.gz
```

备份包内含：`xingtang_cms.sql` + `article/` + 5 个凭据文件 + nginx vhost + systemd 单元。

---

## 三、新服务器：恢复步骤

### 1. 基础环境
```bash
# 宝塔面板安装 nginx + MariaDB（或系统 apt 安装）
apt install -y nginx mariadb-server python3
pip3 install pymysql        # CMS 数据层依赖（2.x）
```

### 2. 解包并放位
```bash
tar -xzf xingtang_migrate_<时间戳>.tar.gz -C /opt/xt_restore
cp -a /opt/xt_restore/article /www/server/nginx/html/article
mkdir -p /www/server/nginx
cp /opt/xt_restore/.xingtang_mysql.json /opt/xt_restore/.xingtang_passwd \
   /opt/xt_restore/.xingtang_wx.json /opt/xt_restore/.htpasswd_xingtang /www/server/nginx/
chmod 600 /www/server/nginx/.xingtang_mysql.json /www/server/nginx/.xingtang_wx.json \
          /www/server/nginx/.htpasswd_xingtang
cp -a /opt/xt_restore/.xingtang_logs /www/server/nginx/ 2>/dev/null || true
```

### 3. 恢复数据库
```bash
# 用备份包里的凭据信息建库建用户（值见 .xingtang_mysql.json）
mysql -uroot -p <<'SQL'
CREATE DATABASE xingtang_cms DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'xingtang_cms'@'127.0.0.1' IDENTIFIED BY '<cms_password>';
CREATE USER 'xingtang_cms'@'localhost' IDENTIFIED BY '<cms_password>';
GRANT ALL PRIVILEGES ON xingtang_cms.* TO 'xingtang_cms'@'127.0.0.1';
GRANT ALL PRIVILEGES ON xingtang_cms.* TO 'xingtang_cms'@'localhost';
FLUSH PRIVILEGES;
SQL
mysql -uxingtang_cms -p'<cms_password>' xingtang_cms < /opt/xt_restore/xingtang_cms.sql
# 若 .xingtang_mysql.json 里的 root_password 与新环境不一致，编辑该文件修正
```

### 4. nginx 配置
```bash
cp /opt/xt_restore/shop.ywye.top.conf /www/server/panel/vhost/nginx/shop.ywye.top.conf
# 或用本地仓库 nginx-cms.conf；核对 server_name / SSL 证书路径 / root 路径
nginx -t && nginx -s reload
```

### 5. SSL 证书
- 方式 A（推荐）：腾讯云 SSL 控制台重新签发/下载新服务器部署
- 方式 B：scp 现有 `fullchain.pem`/`privkey.pem` 到 `/etc/tencent-ssl/shop.ywye.top/`（域名证书不绑定 IP，可沿用；私钥注意安全传输）
- 校验：`openssl x509 -in fullchain.pem -noout -dates`

### 6. CMS 开机自启（systemd）
```bash
cp /opt/xt_restore/cms_server.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now cms_server
systemctl status cms_server
```

### 7. 域名与 CDN
- 修改 DNS A 记录：`shop.ywye.top → 新IP`
- 腾讯云 CDN：把回源地址改为新 IP（或删除加速域名配置，直连源站）
- www 记录：如启用 www 301，同步添加 A 记录

---

## 四、验证清单（迁移后逐项）

```bash
curl -skI https://shop.ywye.top/                # 200 + 安全头 6 项
curl -sk  https://shop.ywye.top/api/public      # news8/courses6/banners4/cities7
curl -sk  https://shop.ywye.top/news/news-01    # SSR 200 + NewsArticle JSON-LD
curl -sk  https://shop.ywye.top/sitemap.xml     # 200 + application/xml
curl -sk -o /dev/null -w "%{http_code}" https://shop.ywye.top/admin/   # 401（basic auth）
# 后台登录（admin / 旧密码）→ 保存/删除一篇测试文章 → MySQL 与 content/ 双写验证
# 前台提交一次测试表单 → leads 落库后删除
# 重启服务器 → curl 确认 CMS 自动拉起（systemd）
```

---

## 五、风险与回滚

| 风险 | 缓解 |
|---|---|
| CMS 无自启 | ✅ 已配置 systemd，重启自动拉起 |
| MySQL 密码/账号不一致 | 凭据在 `.xingtang_mysql.json` 单点维护，改一处即可 |
| 证书/域名切换期服务中断 | 先恢复全部服务并本机验证，再改 DNS/CDN；旧服务器保留 24h 作为回滚点 |
| 数据丢失 | 双保险：MySQL dump + content/*.json 镜像；迁移后先只读验证再停旧站 |
| 回滚 | 恢复 DNS/CDN 回源旧 IP 即回滚（旧服务器服务不动） |
