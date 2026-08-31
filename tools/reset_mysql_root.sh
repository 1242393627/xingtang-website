#!/bin/bash
# 重置 MariaDB root 密码（skip-grant-tables 方式，与 BT 面板 set_mysql_root 同逻辑）
# 仅在本服务器 MariaDB 当前未承载业务时执行（已确认：CMS 用 JSON、无真实 WP 库）
set -u
BASE="/www/server/nginx"

# 1) 生成强密码（仅服务端内存，落盘到 web root 外）
gen() { openssl rand -base64 18 2>/dev/null | tr -dc 'A-Za-z0-9' | head -c 20; }
ROOT_PWD="$(gen)"
APP_PWD="$(gen)"

# 2) 落盘保管（web root 外，600）
cat > "$BASE/.xingtang_mysql.json" <<JSON
{
  "host": "127.0.0.1",
  "port": 3306,
  "root_password": "$ROOT_PWD",
  "cms_db": "xingtang_cms",
  "cms_user": "xingtang_cms",
  "cms_password": "$APP_PWD"
}
JSON
chmod 600 "$BASE/.xingtang_mysql.json"
echo "[1/5] 凭据已写入 $BASE/.xingtang_mysql.json (chmod 600)"

# 3) 停库 -> skip-grant-tables 启动 -> 改密码 -> 重启
echo "[2/5] 停止 mysqld ..."
/etc/init.d/mysqld stop >/dev/null 2>&1
sleep 2
echo "[3/5] skip-grant-tables 启动 ..."
mysqld_safe --skip-grant-tables >/dev/null 2>&1 &
sleep 7
echo "[4/5] 修改 root 密码 ..."
mysql -uroot <<SQL
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY '$ROOT_PWD';
ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY '$ROOT_PWD';
FLUSH PRIVILEGES;
SQL
pkill -9 mysqld_safe >/dev/null 2>&1
pkill -9 mysqld >/dev/null 2>&1
sleep 2
echo "[5/5] 正常启动 mysqld ..."
/etc/init.d/mysqld start >/dev/null 2>&1
sleep 5

# 4) 验证
if mysql -uroot -p"$ROOT_PWD" -e "SELECT VERSION();" >/dev/null 2>&1; then
  echo "OK: root 密码重置成功，可连接"
  mysql -uroot -p"$ROOT_PWD" -e "SELECT VERSION(); SHOW DATABASES;" 2>&1 | head
else
  echo "FAIL: root 仍无法连接，请检查日志"
  exit 1
fi
