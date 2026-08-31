#!/usr/bin/env python3
# 端到端验证：后台保存/删除 -> 写透 MySQL
import urllib.request, json, pymysql

BASE = "http://127.0.0.1:8081"
PW = "Xingtang@2026"

def post(path, payload, headers=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers=headers or {"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())

# 1) 登录
tok = post("/api/login", {"username": "admin", "password": PW})["token"]
H = {"Content-Type": "application/json", "Authorization": "Bearer " + tok}
print("login: token OK")

# 2) 保存测试资讯
item = {"type": "news", "id": "test_mysql",
        "data": {"title": "MySQL写路径测试", "date": "2026-08-18", "category": "招生",
                 "summary": "自动化验证写入", "body": "<p>测试</p>", "image": ""}}
print("save:", post("/api/save", item, H))

# 3) 查 MySQL
cfg = json.load(open("/www/server/nginx/.xingtang_mysql.json"))
c = pymysql.connect(host=cfg["host"], user=cfg["cms_user"], password=cfg["cms_password"],
                    database=cfg["cms_db"], charset="utf8mb4")
cur = c.cursor()
cur.execute("SELECT title, category FROM news WHERE id='test_mysql'")
print("mysql row after save:", cur.fetchall())

# 4) 删除
print("delete:", post("/api/delete", {"type": "news", "id": "test_mysql"}, H))
cur.execute("SELECT COUNT(*) FROM news WHERE id='test_mysql'")
print("mysql count after delete:", cur.fetchone()[0])

# 5) 同时确认公开接口仍 8 篇
pub = json.loads(urllib.request.urlopen(BASE + "/api/public").read())
print("public news count:", len(pub["news"]))
