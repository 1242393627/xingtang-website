#!/bin/bash
# ==================================================
# 星棠官网 · 安全部署脚本
# 用法: bash deploy.sh
# ==================================================
set -euo pipefail

KEY="~/.ssh/your-key.pem"
HOST="root@YOUR_SERVER_IP"
BASE="/www/server/nginx/html/article"

echo "🚀 星棠官网部署"
echo "=============================="

# 1. 备份服务器现有文件
echo "📦 备份服务器文件..."
ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST" "cp $BASE/index.html $BASE/index.html.bak.\$(date +%Y%m%d%H%M%S)"

# 2. 部署文件（防止覆盖错误）
echo "📄 部署 index.html → $BASE/index.html"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new index.html "$HOST:$BASE/"

echo "📁 部署 assets/ → $BASE/assets/"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new -r assets/* "$HOST:$BASE/assets/"

echo "🖥️  部署 admin/ → $BASE/admin/"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new admin/index.html "$HOST:$BASE/admin/"

echo "🐍 部署 cms_server.py → $BASE/"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new cms_server.py "$HOST:$BASE/"

echo "📊 部署 content/ → $BASE/content/"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new -r content/* "$HOST:$BASE/content/"

# 3. 重启 CMS
# 注意：cms_server.py 现在以 MySQL 为主存储，需服务器存在
#   /www/server/nginx/.xingtang_mysql.json（MySQL 连接信息，web root 外，chmod 600）
#   且服务器 python3 已装 pymysql。MySQL 不可用时自动降级读 content/*.json 镜像。
#   用 setsid + stdin 重定向，避免后台进程占用 SSH 通道导致会话卡住。
echo "🔄 重启 CMS 后端..."
ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST" \
  "cd $BASE && fuser -k 8081/tcp 2>/dev/null; sleep 1; setsid python3 cms_server.py > /tmp/cms.log 2>&1 < /dev/null &"

# 4. 验证
sleep 2
echo ""
echo "🔍 验证部署..."
CODE=$(curl -sk -o /dev/null -w "%{http_code}" https://shop.ywye.top/)
echo "  首页: HTTP $CODE"
CODE=$(curl -sk -o /dev/null -w "%{http_code}" https://shop.ywye.top/admin/)
echo "  后台: HTTP $CODE"
CODE=$(curl -sk -o /dev/null -w "%{http_code}" https://shop.ywye.top/api/list?type=courses)
echo "  API:  HTTP $CODE"

echo ""
echo "✅ 部署完成 - https://shop.ywye.top/"
echo "   后台: https://shop.ywye.top/admin/"
echo "   回滚: ssh $HOST 'cp $BASE/index.html.bak.* $BASE/index.html'"
