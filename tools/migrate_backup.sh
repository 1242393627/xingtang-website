#!/bin/bash
# =========================================================
# 星棠官网 · 一键迁移备份（源服务器执行）
# 产出: /root/xingtang_migrate_<时间戳>.tar.gz
# 包含: MySQL dump + web root + 凭据文件 + nginx vhost + systemd 单元
# 注意: SSL 私钥不随包传输（新服务器需重新部署/签发证书）
# =========================================================
set -euo pipefail

TS=$(date +%Y%m%d%H%M%S)
OUT=/root/xingtang_migrate_${TS}.tar.gz
WEB=/www/server/nginx/html/article
SEC=/www/server/nginx
TMP=$(mktemp -d /tmp/xingtang_mig.XXXXXX)

echo "▶ 1/4 导出 MySQL..."
MYSQL_CFG=${SEC}/.xingtang_mysql.json
DB=$(python3 -c "import json;print(json.load(open('${MYSQL_CFG}'))['cms_db'])")
U=$(python3 -c "import json;print(json.load(open('${MYSQL_CFG}'))['cms_user'])")
P=$(python3 -c "import json;print(json.load(open('${MYSQL_CFG}'))['cms_password'])")
mysqldump -u"${U}" -p"${P}" --single-transaction --routines --hex-blob "${DB}" > "${TMP}/xingtang_cms.sql"
echo "   dump: ${TMP}/xingtang_cms.sql ($(du -h "${TMP}/xingtang_cms.sql" | cut -f1))"

echo "▶ 2/4 打包 web root（排除 .bak_*）..."
mkdir -p "${TMP}/article"
rsync -a --exclude='*.bak*' "${WEB}/" "${TMP}/article/"

echo "▶ 3/4 收集凭据与配置..."
cp "${SEC}/.htpasswd_xingtang" "${SEC}/.xingtang_mysql.json" "${SEC}/.xingtang_passwd" "${SEC}/.xingtang_wx.json" "${TMP}/" 2>/dev/null || true
cp -r "${SEC}/.xingtang_logs" "${TMP}/" 2>/dev/null || true
cp /www/server/panel/vhost/nginx/shop.ywye.top.conf "${TMP}/shop.ywye.top.conf" 2>/dev/null || true
[ -f /etc/systemd/system/cms_server.service ] && cp /etc/systemd/system/cms_server.service "${TMP}/cms_server.service" || true

echo "▶ 4/4 生成压缩包..."
tar -czf "${OUT}" -C "${TMP}" .
rm -rf "${TMP}"

echo ""
echo "✅ 迁移包: ${OUT}（$(du -h "${OUT}" | cut -f1)）"
echo "   内含: xingtang_cms.sql / article/ / 5 个凭据文件 / nginx vhost / systemd 单元"
echo "   请勿包含 SSL 私钥传输；新服务器重新部署证书并切换 DNS/CDN 回源。"
