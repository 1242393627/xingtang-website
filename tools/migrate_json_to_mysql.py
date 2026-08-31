#!/usr/bin/env python3
# 将服务器现有 content/*.json 迁移进 MySQL（幂等 upsert，可重复执行）
import json, os, glob, pymysql

CFG_PATH = "/www/server/nginx/.xingtang_mysql.json"
cfg = json.load(open(CFG_PATH, encoding="utf-8"))
conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["cms_user"],
                       password=cfg["cms_password"], database=cfg["cms_db"], charset="utf8mb4")
conn.autocommit = True
cur = conn.cursor()

CONTENT = "/www/server/nginx/html/article/content"

TBL = {
    "settings": "settings_site",
    "courses": "courses",
    "news": "news",
    "banners": "banners",
    "cities": "cities",
    "leads": "leads",
}
COLS = {
    "settings": ["id", "school_name", "phone", "wechat", "slogan", "create_year",
                 "teacher_count", "campus_count", "employment_rate", "course_count"],
    "courses": ["id", "title", "icon", "description", "detail", "image", "order_idx"],
    "news": ["id", "title", "date", "category", "summary", "body", "image"],
    "banners": ["id", "title_en", "title_cn", "subtitle", "link_text", "link_url", "image", "order_idx"],
    "cities": ["id", "name", "name_en", "image", "order_idx"],
    "leads": ["id", "name", "phone", "time", "source"],
}
COL2JSON = {("courses", "order_idx"): "order",
            ("banners", "order_idx"): "order",
            ("cities", "order_idx"): "order"}
INTCOLS = ("order_idx",)


def upsert(t, fname, data):
    cols = COLS[t]
    vals = {}
    for c in cols:
        if c == "id":
            vals[c] = 1 if t == "settings" else fname
            continue
        jk = COL2JSON.get((t, c), c)
        v = data.get(jk)
        if c in INTCOLS:
            try:
                v = int(v) if v not in (None, "") else 0
            except Exception:
                v = 0
        if c == "date" and v in (None, ""):
            v = None
        vals[c] = v
    col_sql = ", ".join("`%s`" % c for c in cols)
    ph = ", ".join(["%s"] * len(cols))
    up = ", ".join("`%s`=%%s" % c for c in cols if c != "id")
    sql = "INSERT INTO `%s` (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s" % (TBL[t], col_sql, ph, up)
    params = [vals[c] for c in cols] + [vals[c] for c in cols if c != "id"]
    cur.execute(sql, params)
    conn.commit()


# settings（单文件）
sp = os.path.join(CONTENT, "settings", "site.json")
if os.path.exists(sp):
    upsert("settings", "site", json.load(open(sp, encoding="utf-8")))
    print("settings: migrated")

# 各列表型
for t in ["courses", "news", "banners", "cities", "leads"]:
    d = os.path.join(CONTENT, t)
    if not os.path.isdir(d):
        continue
    n = 0
    for fp in sorted(glob.glob(os.path.join(d, "*.json"))):
        fname = os.path.basename(fp)[:-5]
        upsert(t, fname, json.load(open(fp, encoding="utf-8")))
        n += 1
    print("%s: %d files" % (t, n))

print("---- 校验行数 ----")
for t in ["settings", "courses", "news", "banners", "cities", "leads"]:
    cur.execute("SELECT COUNT(*) FROM `%s`" % TBL[t])
    print("  %-12s -> %d" % (t, cur.fetchone()[0]))
print("MIGRATION DONE")
