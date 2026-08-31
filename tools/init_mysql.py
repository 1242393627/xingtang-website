#!/usr/bin/env python3
# 初始化 xingtang_cms 专用库、用户、表结构（幂等，可重复执行）
# 读取 web root 外保管文件 /www/server/nginx/.xingtang_mysql.json
import json, pymysql, sys

CFG_PATH = "/www/server/nginx/.xingtang_mysql.json"
cfg = json.load(open(CFG_PATH, encoding="utf-8"))
root_pwd = cfg["root_password"]
cms_user = cfg["cms_user"]
cms_pwd = cfg["cms_password"]
cms_db = cfg["cms_db"]

conn = pymysql.connect(host="127.0.0.1", port=3306, user="root",
                       password=root_pwd, charset="utf8mb4")
conn.autocommit = True
cur = conn.cursor()

# 1) 建库
cur.execute(
    f"CREATE DATABASE IF NOT EXISTS `{cms_db}` "
    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
)
# 2) 建专用用户（localhost + 127.0.0.1）
for h in ("127.0.0.1", "localhost"):
    cur.execute(f"CREATE USER IF NOT EXISTS '{cms_user}'@'{h}' IDENTIFIED BY %s", (cms_pwd,))
    cur.execute(f"GRANT ALL PRIVILEGES ON `{cms_db}`.* TO '{cms_user}'@'{h}'")
cur.execute("FLUSH PRIVILEGES")

cur.execute(f"USE `{cms_db}`")

TABLES = """
CREATE TABLE IF NOT EXISTS settings_site (
  id INT PRIMARY KEY DEFAULT 1,
  school_name VARCHAR(120),
  phone VARCHAR(40),
  wechat VARCHAR(60),
  slogan VARCHAR(200),
  create_year INT,
  teacher_count INT,
  campus_count INT,
  employment_rate INT,
  course_count INT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS courses (
  id VARCHAR(64) PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  icon VARCHAR(10),
  description TEXT,
  detail MEDIUMTEXT,
  image VARCHAR(255),
  order_idx INT DEFAULT 1,
  created_at DATETIME,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS news (
  id VARCHAR(64) PRIMARY KEY,
  title VARCHAR(300) NOT NULL,
  date DATE,
  category VARCHAR(20),
  summary VARCHAR(600),
  body MEDIUMTEXT,
  image VARCHAR(255),
  created_at DATETIME,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS banners (
  id VARCHAR(64) PRIMARY KEY,
  title_en VARCHAR(120),
  title_cn VARCHAR(200),
  subtitle VARCHAR(300),
  link_text VARCHAR(60),
  link_url VARCHAR(255),
  image VARCHAR(255),
  order_idx INT DEFAULT 1,
  created_at DATETIME,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cities (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(100),
  name_en VARCHAR(100),
  image VARCHAR(255),
  order_idx INT DEFAULT 1,
  created_at DATETIME,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS leads (
  id VARCHAR(80) PRIMARY KEY,
  name VARCHAR(100),
  phone VARCHAR(40),
  time DATETIME,
  source VARCHAR(40),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

for stmt in TABLES.split(";"):
    s = stmt.strip()
    if s:
        cur.execute(s)

print("OK: database/user/tables ready ->", cms_db)
cur.execute("SHOW TABLES")
print([r[0] for r in cur.fetchall()])
