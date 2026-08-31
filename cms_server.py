#!/usr/bin/env python3
"""星棠官网·CMS后端——同时支持 Decap CMS 协议 + 简化 REST API"""
import json, os, io, uuid, time, base64, hashlib, re, html, zipfile, datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import urlopen

# Word 导入（python-docx 可选依赖，未安装时接口返回明确错误）
try:
    from docx import Document
    from docx.text.paragraph import Paragraph as _DocxParagraph
    from docx.table import Table as _DocxTable
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False

# MySQL 数据层（可选依赖；未安装时自动降级为 JSON 文件）
try:
    import pymysql
    HAS_PYMYSQL = True
except Exception:
    pymysql = None
    HAS_PYMYSQL = False

CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
ADMIN_USER = "admin"
# 密码存 web root 外的文件（避免被 Nginx 静态服务暴露）
PASSWD_FILE = "/www/server/nginx/.xingtang_passwd"
LOG_DIR = "/www/server/nginx/.xingtang_logs"
DEFAULT_PASS = "Xingtang@2026"
# 动态 token 字典：token -> 过期时间戳（7 天过期）
_TOKENS = {}
TOKEN_EXPIRE = 7 * 24 * 3600
# 招生表单防滥用：按日频控（IP / 手机号）+ 一次性 token 防重放
_SUBMIT_GUARD = {"day": None, "ip": {}, "phone": {}}
_SUBMIT_DAILY_LIMIT = 5
_SUBMIT_TOKENS = {}  # token -> 消费时间戳，10 分钟内仅可消费一次

# ===================== SSR 资讯详情页模板 =====================
# 占位符用 __XXX__，渲染时逐个 .replace()，避免 % / format 与正文内容冲突
NEWS_PAGE_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__ | 星棠化妆培训学校</title>
  <meta name="description" content="__SUMMARY__" />
  <link rel="canonical" href="__OG_URL__" />
  <!-- 头条/字节 时间结构化标签（帮助收录展示真实发布时间） -->
  <meta property="bytedance:published_time" content="__BYTE_PUBLISHED__" />
  <meta property="bytedance:lrDate_time" content="__BYTE_LRDATE__" />
  <meta property="bytedance:updated_time" content="__BYTE_UPDATED__" />
  <!-- 字节跳动/头条 自动推送：页面被访问时自动提交给蜘蛛，提高收录概率 -->
  <script>
  (function () {
    var el = document.createElement("script");
    el.src = "https://lf1-cdn-tos.bytegoofy.com/goofy/ttzz/push.js?4790e9d4aa44ff96332829d5fc8eefc7da55a1ed8b3626bca08e463ecea35a77c112ff4abe50733e0ff1e1071a0fdc024b166ea2a296840a50a5288f35e2ca42";
    el.id = "ttzz";
    var s = document.getElementsByTagName("script")[0];
    s.parentNode.insertBefore(el, s);
  })(window);
  </script>
  <!-- Open Graph -->
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="星棠化妆培训学校" />
  <meta property="og:title" content="__TITLE__" />
  <meta property="og:description" content="__SUMMARY__" />
  <meta property="og:url" content="__OG_URL__" />
  <meta property="og:image" content="__OG_IMAGE__" />
  <meta property="article:published_time" content="__DATE_ISO__" />
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="__TITLE__" />
  <meta name="twitter:description" content="__SUMMARY__" />
  <meta name="twitter:image" content="__OG_IMAGE__" />
  <link rel="stylesheet" href="/assets/css/style.css" />
  <style>
    .article-page{max-width:880px;margin:0 auto;padding:120px 24px 70px;}
    .crumb{font-size:13px;color:#8a8f99;margin-bottom:22px;}
    .crumb a{color:#5a6070;text-decoration:none;}
    .crumb a:hover{color:#260b70;}
    .crumb .sep{margin:0 8px;color:#c5c9d2;}
    .article-title{font-size:30px;line-height:1.35;color:#1a1d26;margin:0 0 16px;font-weight:700;}
    .article-meta{display:flex;align-items:center;gap:14px;font-size:13px;color:#8a8f99;margin-bottom:28px;flex-wrap:wrap;}
    .article-meta .cat{background:#260b70;color:#fff;padding:3px 12px;border-radius:12px;font-size:12px;}
    .article-cover{width:100%;max-height:440px;object-fit:cover;border-radius:12px;margin:0 0 30px;display:block;background:#f0f2f5;}
    .article-body{font-size:16px;line-height:1.95;color:#33353d;}
    .article-body p{margin:0 0 18px;}
    .article-body img{max-width:100%;height:auto;border-radius:8px;margin:18px 0;display:block;}
    .article-body table{border-collapse:collapse;width:100%;margin:18px 0;font-size:15px;}
    .article-body td,.article-body th{border:1px solid #dfe3e8;padding:10px 12px;}
    .article-body tr:nth-child(even){background:#f8f9fb;}
    .article-body h2,.article-body h3{margin:30px 0 14px;color:#1a1d26;line-height:1.4;}
    .article-body h2{font-size:22px;}
    .article-body h3{font-size:19px;}
    .article-body ul,.article-body ol{margin:0 0 18px;padding-left:24px;}
    .article-body li{margin:6px 0;}
    .article-body blockquote{margin:18px 0;padding:12px 18px;border-left:4px solid #260b70;background:#f6f5fb;color:#555;}
    .article-empty-inline{color:#8a8f99;text-align:center;padding:18px 0;}
    .related{margin-top:64px;border-top:1px solid #ebeef2;padding-top:34px;}
    .related h3{font-size:18px;color:#1a1d26;margin:0 0 20px;}
    .related-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;}
    .related-card{display:block;text-decoration:none;background:#fff;border:1px solid #ebeef2;border-radius:8px;padding:18px 18px;transition:all .3s;color:inherit;}
    .related-card:hover{border-color:#260b70;box-shadow:0 10px 30px rgba(38,11,112,.08);transform:translateY(-3px);}
    .related-card .rc-date{font-size:12px;color:#8a8f99;}
    .related-card .rc-title{font-size:15px;margin:6px 0 8px;color:#1a1d26;font-weight:600;line-height:1.4;}
    .related-card .rc-sum{font-size:13px;color:#5a6070;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
    .article-share{margin:30px 0 0;display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:14px;color:#5a6070;}
    .share-btn{display:inline-flex;align-items:center;padding:7px 16px;border:1px solid #dfe3e8;border-radius:20px;background:#fff;color:#33353d;text-decoration:none;font-size:13px;font-family:inherit;cursor:pointer;transition:all .2s;}
    .share-btn:hover{border-color:#260b70;color:#260b70;background:#f6f5fb;}
    .article-pager{display:flex;gap:14px;margin-top:40px;border-top:1px solid #ebeef2;padding-top:26px;flex-wrap:wrap;}
    .pager-item{flex:1 1 45%;display:block;text-decoration:none;color:#33353d;border:1px solid #ebeef2;border-radius:8px;padding:14px 16px;transition:all .25s;min-width:200px;}
    .pager-item:hover{border-color:#260b70;box-shadow:0 8px 24px rgba(38,11,112,.08);}
    .pager-label{display:block;font-size:12px;color:#8a8f99;margin-bottom:6px;}
    .pager-title{font-size:14px;color:#1a1d26;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden;}
    .pager-disabled{opacity:.45;cursor:default;}
    .pager-disabled:hover{border-color:#ebeef2;box-shadow:none;}
    .read-progress{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,#260b70,#5b3bd6);z-index:1000;}
    .back-top{position:fixed;right:22px;bottom:80px;width:44px;height:44px;border-radius:50%;border:none;background:#260b70;color:#fff;font-size:20px;cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:0 8px 20px rgba(38,11,112,.28);z-index:999;}
    .back-top:hover{background:#3a1590;}
    .copy-toast{position:fixed;left:50%;bottom:110px;transform:translateX(-50%);background:rgba(26,29,38,.92);color:#fff;font-size:13px;padding:10px 18px;border-radius:22px;display:none;z-index:1001;max-width:80vw;text-align:center;}
    .wx-modal{position:fixed;inset:0;background:rgba(15,17,24,.55);display:none;align-items:center;justify-content:center;z-index:1002;}
    .wx-modal-box{position:relative;background:#fff;border-radius:14px;padding:28px 24px 24px;text-align:center;max-width:300px;width:calc(100vw - 48px);box-shadow:0 20px 60px rgba(0,0,0,.25);}
    .wx-close{position:absolute;top:8px;right:12px;border:none;background:none;font-size:24px;line-height:1;color:#8a8f99;cursor:pointer;}
    .wx-close:hover{color:#1a1d26;}
    .wx-tip{font-size:14px;color:#33353d;margin:6px 0 16px;}
    .wx-qr{width:220px;height:220px;display:block;margin:0 auto;border:1px solid #ebeef2;border-radius:8px;}
    .wx-fallback{font-size:13px;color:#8a8f99;margin:12px 0;}
    .wx-modal-box .share-btn{margin-top:4px;}
    @media (max-width:768px){
      .article-page{padding:100px 16px 50px;}
      .article-title{font-size:24px;}
      .related-grid{grid-template-columns:1fr;}
      .article-pager{flex-direction:column;}
      .pager-item{flex:1 1 auto;min-width:0;}
      .back-top{right:14px;bottom:70px;}
    }
  </style>
  <script type="application/ld+json">__JSONLD__</script>
</head>
<body>
  <header class="topbar pcheader">
    <div class="topbar-inner">
      <a href="/" class="brand" aria-label="星棠化妆培训学校">
        <img src="/assets/images/logo.png" alt="星棠" class="brand-logo" />
        <span class="brand-cn">星棠化妆培训学校</span>
      </a>
      <div class="topbar-right">
        <div class="hotline">
          <a href="tel:15825263079" class="hotline-tel">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 4h3l2 5-2.5 1.5a11 11 0 005 5L16 13l5 2v3a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z"/></svg>
            <span class="hotline-label">全国统一服务热线</span><b>__PHONE__</b>
          </a>
          <a href="https://shop.ywye.top/" class="hotline-url" target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 4 5.6 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.6-4-9s1.5-6.5 4-9z"/></svg>
            <span>官网：shop.ywye.top</span>
          </a>
        </div>
        <a href="/#recruit" class="icon-btn" aria-label="立即咨询" style="text-decoration:none;color:inherit;">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
        </a>
      </div>
    </div>
  </header>

  <nav class="mainnav" id="mainnav" aria-label="主导航">
    <ul class="nav-list">
      <li class="nav-item"><a href="/#courses">热门课程</a></li>
      <li class="nav-item"><a href="/#teachers">名师团队</a></li>
      <li class="nav-item"><a href="/#world">星棠世界</a></li>
      <li class="nav-item"><a href="/#recruit">招生流程</a></li>
      <li class="nav-item"><a href="/#env">校区环境</a></li>
      <li class="nav-item"><a href="/#works">学员作品</a></li>
      <li class="nav-item"><a href="/#career">就业创业</a></li>
      <li class="nav-item"><a href="/#brands">合作品牌</a></li>
      <li class="nav-item"><a href="/#studio">资讯动态</a></li>
    </ul>
  </nav>

  <main class="article-page">
    <nav class="crumb" aria-label="面包屑">
      <a href="/">首页</a><span class="sep">&rsaquo;</span>
      <a href="/#studio">资讯动态</a><span class="sep">&rsaquo;</span>
      <span>__TITLE__</span>
    </nav>
    <article>
      <h1 class="article-title">__TITLE__</h1>
      <div class="article-meta">
        <span class="cat">__CAT__</span>
        <span>__DATE_DISPLAY__</span>
      </div>
      __COVER__
      <div class="article-body">__BODY__</div>
      __SHARE__
    </article>
    __PREVNEXT__
    __RELATED__
  </main>

  <footer class="footer">
    <div class="footer-top">
      <div class="foot-col foot-brand">
        <img src="/assets/images/logo.png" alt="星棠" class="foot-logo" />
        <p class="foot-slogan">以技术为根 · 以审美为魂</p>
        <p class="foot-hot">全国统一服务热线 <b>__PHONE__</b></p>
        <p class="foot-wx">官方微信：158 2526 3079（微信同号）</p>
      </div>
      <div class="foot-col">
        <h5>快速导航</h5>
        <a href="/#world">星棠世界</a>
        <a href="/#courses">课程设置</a>
        <a href="/#env">校区环境</a>
        <a href="/#works">学员作品</a>
        <a href="/#recruit">招生流程</a>
      </div>
      <div class="foot-col">
        <h5>热门课程</h5>
        <a href="/#courses">个人形象提升班</a>
        <a href="/#courses">时尚彩妆造型班</a>
        <a href="/#courses">化妆精品研修班</a>
        <a href="/#courses">化妆高阶创业班</a>
      </div>
      <div class="foot-col">
        <h5>友情链接</h5>
        <a href="#" rel="nofollow">中国美发美容协会</a>
        <a href="#" rel="nofollow">美妆教育联盟</a>
        <a href="#" rel="nofollow">彩妆资讯</a>
      </div>
    </div>
    <div class="footer-bottom">
      <p>Copyright &copy; 2018-2026 星棠化妆培训学校</p>
      <p class="foot-links">
        <a href="#">办学资质与许可证以各校区公示为准</a>
        <a href="#">隐私政策</a>
        <a href="#">免责声明</a>
      </p>
    </div>
  </footer>

  <div class="read-progress" id="readProgress"></div>
  <button class="back-top" id="backTop" type="button" aria-label="返回顶部">&uarr;</button>
  <script>
  (function () {
    'use strict';
    function $(s) { return document.getElementById(s); }
    var bar = $('readProgress'), bt = $('backTop');
    function onScroll() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      if (bar) bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
      if (bt) bt.style.display = h.scrollTop > 400 ? 'flex' : 'none';
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    if (bt) bt.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    function showToast(msg) {
      var t = $('copyToast');
      if (!t) { t = document.createElement('div'); t.id = 'copyToast'; t.className = 'copy-toast'; document.body.appendChild(t); }
      t.textContent = msg; t.style.display = 'block';
      clearTimeout(t._timer);
      t._timer = setTimeout(function () { t.style.display = 'none'; }, 2200);
    }
    function fallbackCopy(text) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', '');
      ta.style.position = 'fixed'; ta.style.left = '-9999px';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
    }
    function copyCurrentLink() {
      var url = location.href, msg = '链接已复制，可粘贴到微信 / 朋友圈分享';
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { showToast(msg); }, function () { fallbackCopy(url); showToast(msg); });
      } else {
        fallbackCopy(url); showToast(msg);
      }
    }
    var cp = $('copyLinkBtn');
    if (cp) cp.addEventListener('click', copyCurrentLink);
    var cp2 = $('copyLinkBtn2');
    if (cp2) cp2.addEventListener('click', copyCurrentLink);
    // 微信分享：微信内走 JS-SDK 一键转发，微信外弹二维码扫码
    var isWeChat = /MicroMessenger/i.test(navigator.userAgent);
    var wxModal = $('wxModal'), wxBtn = $('wxShareBtn'), wxClose = $('wxClose'), wxQr = $('wxQr'), wxFallback = $('wxFallback');
    function openWx() { if (wxModal) { wxModal.style.display = 'flex'; document.body.style.overflow = 'hidden'; } }
    function closeWx() { if (wxModal) { wxModal.style.display = 'none'; document.body.style.overflow = ''; } }
    if (wxBtn) wxBtn.addEventListener('click', function () {
      if (isWeChat) { showToast('请点击右上角「···」分享给好友或朋友圈'); }
      else { openWx(); }
    });
    if (wxClose) wxClose.addEventListener('click', closeWx);
    if (wxModal) wxModal.addEventListener('click', function (e) { if (e.target === wxModal) closeWx(); });
    if (wxQr) wxQr.addEventListener('error', function () { if (wxFallback) wxFallback.style.display = 'block'; wxQr.style.display = 'none'; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeWx(); });
    // 微信 JS-SDK：配置分享标题/摘要/封面
    function initWxShare() {
      var link = location.href.split('#')[0];
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/api/wx-sign?url=' + encodeURIComponent(link));
      xhr.onload = function () {
        try {
          var d = JSON.parse(xhr.responseText);
          if (!d.appid || !d.signature) return;
          var mt = function (p) { var el = document.querySelector('meta[property="' + p + '"]'); return el ? el.getAttribute('content') : ''; };
          var share = { title: mt('og:title') || document.title, desc: mt('og:description'), link: link, imgUrl: mt('og:image') };
          wx.config({ debug: false, appId: d.appid, timestamp: d.timestamp, nonceStr: d.nonceStr, signature: d.signature, jsApiList: ['updateAppMessageShareData', 'updateTimelineShareData', 'onMenuShareAppMessage', 'onMenuShareTimeline'] });
          wx.ready(function () {
            wx.updateAppMessageShareData(share);
            wx.updateTimelineShareData({ title: share.title, link: share.link, imgUrl: share.imgUrl });
            wx.onMenuShareAppMessage(share);
            wx.onMenuShareTimeline({ title: share.title, link: share.link, imgUrl: share.imgUrl });
          });
        } catch (e) {}
      };
      xhr.send();
    }
    if (isWeChat) {
      if (typeof wx !== 'undefined') { initWxShare(); }
      else {
        var ws = document.createElement('script');
        ws.src = 'https://res.wx.qq.com/open/js/jweixin-1.6.0.js';
        ws.onload = initWxShare;
        document.head.appendChild(ws);
      }
    }
  })();
  </script>
</body>
</html>
"""

NEWS_404_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>文章不存在 | 星棠化妆培训学校</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="/assets/css/style.css"></head>
<body style="margin:0;font-family:system-ui,'Microsoft YaHei',sans-serif;">
<main class="article-page" style="text-align:center;padding-top:160px;">
  <h1 style="font-size:30px;color:#1a1d26;">未找到该资讯</h1>
  <p style="color:#8a8f99;">文章可能已被删除或链接有误。</p>
  <p><a href="/#studio" style="color:#260b70;text-decoration:none;font-weight:600;">返回资讯动态 &rsaquo;</a></p>
</main></body></html>"""

def _load_passwd():
    if os.path.exists(PASSWD_FILE):
        with open(PASSWD_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or DEFAULT_PASS
    return DEFAULT_PASS

def _save_passwd(pwd):
    with open(PASSWD_FILE, "w", encoding="utf-8") as f:
        f.write(pwd)

def _log(action, detail=""):
    """写操作日志（web root 外）"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        fname = time.strftime("%Y-%m-%d") + ".jsonl"
        with open(os.path.join(LOG_DIR, fname), "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action, "detail": detail}, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _read_logs(limit=200):
    result = []
    try:
        files = sorted(os.listdir(LOG_DIR)) if os.path.isdir(LOG_DIR) else []
        for fname in reversed(files):
            with open(os.path.join(LOG_DIR, fname), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try: result.append(json.loads(line))
                        except Exception: pass
            if len(result) >= limit: break
    except Exception:
        pass
    return result[:limit]

def _cleanup_tokens():
    now = time.time()
    for t in [k for k, v in _TOKENS.items() if v < now]:
        del _TOKENS[t]

def _make_token():
    """生成一个 7 天过期的随机 token，写入字典，返回 (token, expires_in)"""
    _cleanup_tokens()
    token = uuid.uuid4().hex + uuid.uuid4().hex
    _TOKENS[token] = time.time() + TOKEN_EXPIRE
    return token, TOKEN_EXPIRE

# ===================== 微信 JS-SDK 签名（公众号 JSSDK） =====================
WX_CONFIG_FILE = "/www/server/nginx/.xingtang_wx.json"
_WX_CACHE = {"token": None, "token_exp": 0, "ticket": None, "ticket_exp": 0}

def _load_wx_config():
    try:
        if os.path.exists(WX_CONFIG_FILE):
            with open(WX_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _wx_http_get(url):
    with urlopen(url, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _wx_get_token(cfg):
    now = time.time()
    if _WX_CACHE["token"] and _WX_CACHE["token_exp"] > now:
        return _WX_CACHE["token"]
    try:
        data = _wx_http_get(
            "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"
            % (cfg.get("appid", ""), cfg.get("appsecret", "")))
        tok = data.get("access_token", "")
        if tok:
            _WX_CACHE["token"] = tok
            _WX_CACHE["token_exp"] = now + int(data.get("expires_in", 7200)) - 300
        return tok
    except Exception:
        return ""

def _wx_get_ticket(cfg, token):
    now = time.time()
    if _WX_CACHE["ticket"] and _WX_CACHE["ticket_exp"] > now:
        return _WX_CACHE["ticket"]
    try:
        data = _wx_http_get(
            "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=%s&type=jsapi" % token)
        t = data.get("ticket", "")
        if t:
            _WX_CACHE["ticket"] = t
            _WX_CACHE["ticket_exp"] = now + int(data.get("expires_in", 7200)) - 300
        return t
    except Exception:
        return ""

def _wx_signature(ticket, noncestr, timestamp, url):
    raw = "jsapi_ticket=%s&noncestr=%s&timestamp=%s&url=%s" % (ticket, noncestr, timestamp, url)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

# ===================== Word(.docx) → HTML 导入 =====================
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_V = "urn:schemas-microsoft-com:vml"
_NS_O = "urn:schemas-microsoft-com:office:office"

def _docx_to_html(blob, out_dir):
    """把 .docx 字节内容转 HTML。图片保存到 out_dir（content/uploads）。
    返回 (html, para_count, img_count, media_total)"""
    os.makedirs(out_dir, exist_ok=True)
    doc = Document(io.BytesIO(blob))
    parts = []
    para_count = 0
    img_count = 0
    list_buf = None  # [tag, [items]]

    # 文档包里 word/media/ 媒体总数（诊断：与 img_count 对比可知漏了多少）
    media_total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            media_total = len([n for n in z.namelist() if n.startswith("word/media/")])
    except Exception:
        pass

    def flush_list():
        nonlocal list_buf
        if list_buf and list_buf[1]:
            tag = list_buf[0]
            parts.append("<%s><li>%s</li></%s>" % (tag, "</li><li>".join(list_buf[1]), tag))
        list_buf = None

    def run_html(run):
        nonlocal img_count
        out = []
        # 行内图片：兼容 DrawingML(a:blip/r:embed) 与 VML(v:imagedata/r:id 或 o:relid)
        rids = []
        for blip in run._element.iter("{%s}blip" % _NS_A):
            rid = blip.get("{%s}embed" % _NS_R) or blip.get("{%s}link" % _NS_R)
            if rid: rids.append(rid)
        for im in run._element.iter("{%s}imagedata" % _NS_V):
            rid = im.get("{%s}id" % _NS_R) or im.get("{%s}relid" % _NS_O)
            if rid: rids.append(rid)
        for rid in rids:
            part = doc.part.related_parts.get(rid)
            if part is None:
                continue
            try:
                ct = getattr(part, "content_type", "") or "image/png"
                ext = ct.split("/")[-1]
                if ext == "jpeg": ext = "jpg"
                if ext not in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
                    ext = "png"
                fname = "docx_%d_%s.%s" % (int(time.time()), uuid.uuid4().hex[:6], ext)
                with open(os.path.join(out_dir, fname), "wb") as f:
                    f.write(part.blob)
                out.append('<img src="/content/uploads/%s" alt="" loading="lazy" decoding="async" />' % fname)
                img_count += 1
            except Exception:
                pass
        if run.text:
            t = html.escape(run.text)
            if run.bold: t = "<strong>%s</strong>" % t
            if run.italic: t = "<em>%s</em>" % t
            if run.underline: t = "<u>%s</u>" % t
            out.append(t)
        return "".join(out)

    for block in doc.iter_inner_content():
        if isinstance(block, _DocxParagraph):
            txt = "".join(run_html(r) for r in block.runs)
            if not txt.strip():
                flush_list()
                continue
            style = (block.style.name or "") if block.style else ""
            para_count += 1
            if style == "Title" or "Heading 1" in style:
                flush_list(); parts.append("<h2>%s</h2>" % txt)
            elif "Heading 2" in style:
                flush_list(); parts.append("<h3>%s</h3>" % txt)
            elif "Heading 3" in style:
                flush_list(); parts.append("<h4>%s</h4>" % txt)
            elif "List Bullet" in style:
                if not (list_buf and list_buf[0] == "ul"): flush_list(); list_buf = ["ul", []]
                list_buf[1].append(txt)
            elif "List Number" in style:
                if not (list_buf and list_buf[0] == "ol"): flush_list(); list_buf = ["ol", []]
                list_buf[1].append(txt)
            else:
                flush_list(); parts.append("<p>%s</p>" % txt)
        elif isinstance(block, _DocxTable):
            flush_list()
            rows = []
            for row in block.rows:
                cells = []
                for cell in row.cells:
                    ch = "".join(run_html(r) for p in cell.paragraphs for r in p.runs)
                    if not ch.strip():
                        ch = html.escape(cell.text.strip())
                    cells.append("<td>%s</td>" % ch)
                rows.append("<tr>%s</tr>" % "".join(cells))
            if rows:
                parts.append('<table><tbody>%s</tbody></table>' % "".join(rows))
    flush_list()
    return "".join(parts), para_count, img_count, media_total

for sub in ["settings","courses","news","banners","cities","uploads","leads"]:
    os.makedirs(os.path.join(CONTENT_DIR, sub), exist_ok=True)

def _safe_path(folder):
    """校验路径，防止 ../ 路径遍历逃出 CONTENT_DIR"""
    base = os.path.realpath(CONTENT_DIR)
    target = os.path.realpath(os.path.join(CONTENT_DIR, folder))
    if target != base and not target.startswith(base + os.sep):
        return None
    return target


# ===================== MySQL 数据层（主） + JSON 文件（兜底/镜像） =====================
_MYSQL_CFG = None
_DB_CONN = None

def _mysql_cfg():
    global _MYSQL_CFG
    if _MYSQL_CFG is None:
        for p in ("/www/server/nginx/.xingtang_mysql.json",
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), ".xingtang_mysql.json")):
            if os.path.exists(p):
                try:
                    _MYSQL_CFG = json.load(open(p, encoding="utf-8"))
                except Exception:
                    _MYSQL_CFG = False
                break
        else:
            _MYSQL_CFG = False
    return _MYSQL_CFG or {}

def _db():
    global _DB_CONN
    if not HAS_PYMYSQL:
        return None
    cfg = _mysql_cfg()
    if not cfg:
        return None
    try:
        if _DB_CONN is None or not getattr(_DB_CONN, "open", False):
            _DB_CONN = pymysql.connect(
                host=cfg.get("host", "127.0.0.1"), port=int(cfg.get("port", 3306)),
                user=cfg.get("cms_user"), password=cfg.get("cms_password"),
                database=cfg.get("cms_db"), charset="utf8mb4",
                autocommit=True, connect_timeout=3,
            )
        try:
            _DB_CONN.ping()
        except Exception:
            _DB_CONN = None
            return None
        return _DB_CONN
    except Exception:
        _DB_CONN = None
        return None

_TABLE = {
    "settings": "settings_site",
    "courses": "courses",
    "news": "news",
    "banners": "banners",
    "cities": "cities",
    "leads": "leads",
}
_COLS = {
    "settings": ["id", "school_name", "phone", "wechat", "slogan", "create_year",
                 "teacher_count", "campus_count", "employment_rate", "course_count"],
    "courses": ["id", "title", "icon", "description", "detail", "image", "order_idx"],
    "news": ["id", "title", "date", "category", "summary", "body", "image"],
    "banners": ["id", "title_en", "title_cn", "subtitle", "link_text", "link_url", "image", "order_idx"],
    "cities": ["id", "name", "name_en", "image", "order_idx"],
    "leads": ["id", "name", "phone", "time", "source"],
}
_COL2JSON = {("courses", "order_idx"): "order",
             ("banners", "order_idx"): "order",
             ("cities", "order_idx"): "order"}
_INTCOLS = ("order_idx",)

def _row_to_json(t, row):
    if row is None:
        return None
    d = dict(row)
    d.pop("created_at", None)
    d.pop("updated_at", None)
    pk = d.pop("id", None)
    if "order_idx" in d:
        d["order"] = d.pop("order_idx")
    if t == "news" and isinstance(d.get("date"), (datetime.date, datetime.datetime)):
        d["date"] = d["date"].strftime("%Y-%m-%d")
    if t == "leads" and isinstance(d.get("time"), datetime.datetime):
        d["time"] = d["time"].strftime("%Y-%m-%d %H:%M:%S")
    d["_id"] = "site" if t == "settings" else (pk or "")
    return d

def _db_list(t):
    if t not in _COLS:
        return None
    conn = _db()
    if conn is None:
        return None
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        if t == "settings":
            cur.execute("SELECT * FROM settings_site LIMIT 1")
            return [_row_to_json("settings", cur.fetchone())]
        order = "date DESC, id ASC" if t == "news" else "order_idx ASC, id ASC"
        cur.execute("SELECT * FROM `%s` ORDER BY %s" % (_TABLE[t], order))
        return [_row_to_json(t, r) for r in cur.fetchall()]
    except Exception:
        return None

def _db_get(t, fname):
    if t not in _COLS:
        return None
    conn = _db()
    if conn is None:
        return None
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        if t == "settings":
            cur.execute("SELECT * FROM settings_site LIMIT 1")
            return _row_to_json("settings", cur.fetchone())
        cur.execute("SELECT * FROM `%s` WHERE id=%%s" % _TABLE[t], (fname,))
        return _row_to_json(t, cur.fetchone())
    except Exception:
        return None

def _db_save(t, fname, data):
    if t not in _COLS:
        return
    conn = _db()
    if conn is None:
        return
    try:
        cols = _COLS[t]
        vals = {}
        for c in cols:
            if c == "id":
                vals[c] = 1 if t == "settings" else fname
                continue
            jk = _COL2JSON.get((t, c), c)
            v = data.get(jk)
            if c in _INTCOLS:
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
        sql = "INSERT INTO `%s` (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s" % (_TABLE[t], col_sql, ph, up)
        params = [vals[c] for c in cols] + [vals[c] for c in cols if c != "id"]
        conn.cursor().execute(sql, params)
        conn.commit()
    except Exception:
        pass

def _db_delete(t, fname):
    if t not in _COLS:
        return
    conn = _db()
    if conn is None:
        return
    try:
        if t == "settings":
            conn.cursor().execute("DELETE FROM settings_site")
        else:
            conn.cursor().execute("DELETE FROM `%s` WHERE id=%%s" % _TABLE[t], (fname,))
        conn.commit()
    except Exception:
        pass


# ---- JSON 文件兜底/镜像 ----
def _list_file(folder):
    d = _safe_path(folder)
    if not d or not os.path.isdir(d):
        return []
    result = []
    for fname in sorted(os.listdir(d)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(d, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            data["_id"] = fname.replace(".json", "")
            result.append(data)
    return result

def _read_file(filepath):
    path = _safe_path(filepath)
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _write_file(filepath, data):
    path = _safe_path(filepath)
    if not path:
        return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _delete_file(filepath):
    path = _safe_path(filepath)
    if not path or not os.path.exists(path):
        return
    try:
        os.remove(path)
    except Exception:
        pass


# ---- 对外统一接口：MySQL 优先，JSON 兜底/镜像 ----
def _list(folder):
    rows = _db_list(folder)
    if rows is None:                      # MySQL 不可用 -> 走 JSON 文件
        return _list_file(folder)
    if not rows and folder in _COLS:      # MySQL 空但文件有数据 -> 兜底（防建表未迁移/误清空）
        fr = _list_file(folder)
        if fr:
            return fr
    return rows

def _read(filepath):
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) == 2 and parts[1].endswith(".json"):
        item = _db_get(parts[0], parts[1][:-5])
        if item is not None:
            return item
    return _read_file(filepath)

def _write(filepath, data):
    ok = _write_file(filepath, data)      # 始终写 JSON 镜像（兜底/回滚）
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) == 2 and parts[1].endswith(".json"):
        _db_save(parts[0], parts[1][:-5], data)   # 尽力写 MySQL
    return ok

def _delete(filepath):
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) == 2 and parts[1].endswith(".json"):
        _db_delete(parts[0], parts[1][:-5])
    _delete_file(filepath)

class CMS(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _serve_sitemap(self):
        """动态生成 sitemap.xml：首页 + 全部资讯文章，随发布自动更新 lastmod"""
        from xml.sax.saxutils import escape as xesc
        today = datetime.date.today().isoformat()
        site = "https://shop.ywye.top"
        rows = [(site + "/", today, "weekly", "1.0")]
        for n in _list("news"):
            nid = n.get("_id")
            if not nid:
                continue
            lm = str(n.get("date") or today)
            rows.append((site + "/news/" + nid, lm, "monthly", "0.6"))
        parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for loc, lm, cf, pr in rows:
            parts.append('  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>'
                         % (xesc(loc), lm, cf, pr))
        parts.append("</urlset>")
        data = "\n".join(parts).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _auth(self):
        auth = self.headers.get("Authorization","")
        token = auth.replace("Bearer ","").strip()
        if not token or token not in _TOKENS:
            return False
        if _TOKENS[token] < time.time():
            del _TOKENS[token]
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    # ======== 简化 REST API ========
    def _api_list(self, qs):
        t = qs.get("type",[""])[0]
        if not t: return self._json({"error":"type required"}, 400)
        return self._json({"data":_list(t)})

    def _api_get(self, qs):
        t, id = qs.get("type",[""])[0], qs.get("id",[""])[0]
        entry = _read(f"{t}/{id}.json")
        if entry: entry["_id"] = id; return self._json({"data":entry})
        return self._json({"error":"Not found"}, 404)

    def _api_save(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        t = body.get("type"); data = body.get("data",{})
        id = body.get("id","") or data.get("_id","") or str(uuid.uuid4())[:8]
        data.pop("_id",None); data.pop("type",None)
        if not _write(f"{t}/{id}.json", data):
            return self._json({"error":"非法路径"}, 400)
        _log("save", f"{t}/{id}")
        return self._json({"id":id,"ok":True})

    def _api_delete(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        _delete(f"{body['type']}/{body['id']}.json")
        _log("delete", f"{body['type']}/{body['id']}")
        return self._json({"ok":True})

    def _api_batchdelete(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        t = body.get("type"); ids = body.get("ids",[])
        n = 0
        for id in ids:
            if _safe_path(f"{t}/{id}.json"):
                _delete(f"{t}/{id}.json")
                n += 1
        _log("batchdelete", f"{t} ×{n}")
        return self._json({"ok":True,"count":n})

    def _api_changepwd(self, body):
        old = (body.get("old_pwd") or "").strip()
        new = (body.get("new_pwd") or "").strip()
        if _load_passwd() != old:
            return self._json({"error":"原密码错误"}, 401)
        if len(new) < 8:
            return self._json({"error":"新密码至少 8 位"}, 400)
        _save_passwd(new)
        _log("changepwd", "密码已修改")
        return self._json({"ok":True,"msg":"密码修改成功"})

    def _api_submit(self, body):
        """保存线索到 content/leads/（手机号格式校验 + 频控 + 一次性 token 防重放）"""
        import time as _time
        name = (body.get("name") or "").strip()
        phone = (body.get("phone") or "").strip()
        if not name or not phone:
            return self._json({"ok":False,"error":"姓名和联系电话不能为空"},400)
        # 手机号格式服务端校验（中国大陆 11 位）
        if not re.match(r"^1[3-9]\d{9}$", phone):
            return self._json({"ok":False,"error":"联系电话格式不正确"},400)
        # 一次性 token：防重复提交/重放（前端每次提交生成新 token）
        tk = str(body.get("t") or "")
        now = _time.time()
        if not tk:
            return self._json({"ok":False,"error":"缺少提交令牌，请刷新页面后重试"},400)
        if tk in _SUBMIT_TOKENS:
            return self._json({"ok":False,"error":"请勿重复提交"},400)
        _SUBMIT_TOKENS[tk] = now
        for k in [k for k, v in _SUBMIT_TOKENS.items() if now - v > 600]:
            _SUBMIT_TOKENS.pop(k, None)
        # 频控：同 IP / 同手机号 每日 N 次
        today = _time.strftime("%Y-%m-%d")
        if _SUBMIT_GUARD["day"] != today:
            _SUBMIT_GUARD["day"] = today
            _SUBMIT_GUARD["ip"] = {}
            _SUBMIT_GUARD["phone"] = {}
        ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        _SUBMIT_GUARD["ip"][ip] = _SUBMIT_GUARD["ip"].get(ip, 0) + 1
        _SUBMIT_GUARD["phone"][phone] = _SUBMIT_GUARD["phone"].get(phone, 0) + 1
        if _SUBMIT_GUARD["ip"][ip] > _SUBMIT_DAILY_LIMIT or _SUBMIT_GUARD["phone"][phone] > _SUBMIT_DAILY_LIMIT:
            return self._json({"ok":False,"error":"今日提交次数过多，请明天再试"},429)
        os.makedirs(os.path.join(CONTENT_DIR,"leads"), exist_ok=True)
        lead = {
            "name": name,
            "phone": phone,
            "time": _time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "web_form"
        }
        fname = f"lead_{int(_time.time())}_{uuid.uuid4().hex[:4]}.json"
        _write(f"leads/{fname}", lead)
        return self._json({"ok":True,"msg":"提交成功，课程顾问将尽快与您联系"})

    def _api_upload(self):
        ct = self.headers.get("Content-Type","")
        length = int(self.headers.get("Content-Length",0))
        if length > 5 * 1024 * 1024:  # 限制 5MB
            return self._json({"error":"文件过大，最大 5MB"}, 413)
        body = self.rfile.read(length)
        if "multipart" in ct:
            boundary = ct.split("boundary=")[1]
            parts = body.split(f"--{boundary}".encode())
            for part in parts:
                if b"filename=" in part:
                    header, content = part.split(b"\r\n\r\n",1)
                    content = content.rsplit(b"\r\n",1)[0]
                    return self._save_upload(content)
        else:
            return self._save_upload(body)
        return self._json({"error":"无文件"}, 400)

    def _save_upload(self, content):
        """校验图片魔数并保存，防止上传恶意文件"""
        if not content:
            return self._json({"error":"空文件"}, 400)
        # 图片文件头魔数校验：jpg / png / gif / webp
        jpg = content[:3] == b'\xff\xd8\xff'
        png = content[:8] == b'\x89PNG\r\n\x1a\n'
        gif = content[:6] in (b'GIF87a', b'GIF89a')
        webp = content[:4] == b'RIFF' and content[8:12] == b'WEBP'
        if not (jpg or png or gif or webp):
            return self._json({"error":"仅支持图片文件"}, 400)
        ext = 'jpg' if jpg else 'png' if png else 'gif' if gif else 'webp'
        fname = f"{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
        with open(os.path.join(CONTENT_DIR,"uploads",fname),"wb") as f:
            f.write(content)
        return self._json({"url":f"/content/uploads/{fname}","name":fname})

    # ======== Router ========
    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/api/login": return self._json({"error":"Method Not Allowed"},405)
        # 网站地图（动态生成，随发布自动更新）
        if p.path == "/sitemap.xml": return self._serve_sitemap()
        # ===== SSR: 资讯详情页（SEO 友好，完整 HTML 含 JSON-LD，公开无需鉴权） =====
        m = re.match(r"^/news/([\w\-]+)$", p.path)
        if m:
            return self._serve_news(m.group(1))
        # 公开聚合接口：前端网站渲染用（不含 leads 隐私数据）
        if p.path == "/api/public":
            return self._json({
                "settings": _read("settings/site.json") or {},
                "courses": _list("courses"),
                "news": _list("news"),
                "banners": _list("banners"),
                "cities": _list("cities")
            })
        # 微信 JS-SDK 签名（公开，前端微信内分享用）
        if p.path == "/api/wx-sign":
            return self._api_wx_sign(parse_qs(p.query))
        # 所有数据接口一律要求鉴权（防止 /api/list?type=leads 泄露留资隐私）
        if not self._auth(): return self._json({"error":"Unauthorized"},401)
        if p.path == "/api/list": return self._api_list(parse_qs(p.query))
        if p.path == "/api/get": return self._api_get(parse_qs(p.query))
        if p.path == "/api/leads": return self._json({"data":_list("leads")})
        if p.path == "/api/logs": return self._json({"data":_read_logs()})
        self._json({"error":"Not found"},404)

    def do_POST(self):
        p = urlparse(self.path)
        if p.path == "/api/login":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
            if body.get("username")==ADMIN_USER and body.get("password")==_load_passwd():
                token, exp = _make_token()
                _log("login", "登录成功")
                return self._json({"token":token,"expires_in":exp,"ok":True})
            _log("login", "登录失败")
            return self._json({"error":"用户名或密码错误"},401)
        if p.path == "/api/changepwd":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
            return self._api_changepwd(body)
        if p.path == "/api/submit":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
            return self._api_submit(body)
        if not self._auth(): return self._json({"error":"Unauthorized"},401)
        if p.path == "/api/save": return self._api_save()
        if p.path == "/api/delete": return self._api_delete()
        if p.path == "/api/batchdelete": return self._api_batchdelete()
        if p.path == "/api/upload": return self._api_upload()
        if p.path == "/api/import-docx": return self._api_import_docx()
        # Legacy Git Gateway support
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        action = body.get("action","")
        if action == "login":
            if body.get("email","")==ADMIN_USER and body.get("password","")==_load_passwd():
                token, exp = _make_token()
                return self._json({"access_token":token,"token_type":"bearer","expires_in":exp})
            return self._json({"error":"wrong"},401)
        if action == "entriesByFolder":
            folder = body.get("params",{}).get("folder","").replace("content/","")
            return self._json(_list(folder))
        if action == "entriesByFiles":
            files = body.get("params",{}).get("files",[])
            entries = []
            for f in files:
                fp = f.get("path","").replace("content/","")
                d = _read(fp)
                if d: entries.append({"file":{"path":f.get("path",""),"label":f.get("label","")},"data":d})
            return self._json(entries)
        if action == "getEntry":
            c = body.get("params",{}).get("collection","")
            slug = body.get("params",{}).get("slug","")
            fp = body.get("params",{}).get("path","").replace("content/","")
            d = _read(f"{c}/{slug}.json") if slug else _read(fp) if fp else None
            if d:
                d["slug"] = slug or fp.split("/")[-1].replace(".json","")
                d["path"] = fp or f"content/{c}/{slug}.json"
                return self._json(d)
            return self._json({"error":"Not found"},404)
        if action == "persistEntry":
            c = body.get("params",{}).get("collection","")
            slug = body.get("params",{}).get("slug","") or str(uuid.uuid4())[:8]
            _write(f"{c}/{slug}.json", body.get("params",{}).get("entryData",{}))
            return self._json({"slug":slug})
        if action == "deleteEntry":
            _delete(f"{body['params']['collection']}/{body['params']['slug']}.json")
            return self._json({})
        if action == "getMedia":
            d = os.path.join(CONTENT_DIR,"uploads")
            files = []
            for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                fp = os.path.join(d,f)
                if os.path.isfile(fp):
                    files.append({"name":f,"path":f"content/uploads/{f}","url":f"/content/uploads/{f}","size":os.path.getsize(fp)})
            return self._json(files)
        if action == "persistMedia":
            b64 = body.get("params",{}).get("fileData","")
            fn = body.get("params",{}).get("fileName","") or f"{int(time.time())}.jpg"
            if b64:
                with open(os.path.join(CONTENT_DIR,"uploads",fn),"wb") as f:
                    f.write(base64.b64decode(b64))
            return self._json({"name":fn,"url":f"/content/uploads/{fn}"})
        self._json({"error":f"Unknown action: {action}"},404)

    # ======== 微信 JS-SDK 签名接口 ========
    def _api_wx_sign(self, qs):
        cfg = _load_wx_config()
        if not cfg.get("appid") or not cfg.get("appsecret"):
            return self._json({"error": "wx not configured"}, 500)
        url = qs.get("url", [""])[0]
        token = _wx_get_token(cfg)
        if not token:
            return self._json({"error": "access_token failed"}, 500)
        ticket = _wx_get_ticket(cfg, token)
        if not ticket:
            return self._json({"error": "jsapi_ticket failed"}, 500)
        noncestr = uuid.uuid4().hex[:16]
        timestamp = str(int(time.time()))
        return self._json({
            "appid": cfg["appid"],
            "timestamp": timestamp,
            "nonceStr": noncestr,
            "signature": _wx_signature(ticket, noncestr, timestamp, url)
        })

    # ======== Word 导入（docx → HTML） ========
    def _api_import_docx(self):
        if not HAS_DOCX:
            return self._json({"error": "服务器未安装 python-docx，无法解析 Word"}, 500)
        ct = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        if length > 10 * 1024 * 1024:
            return self._json({"error": "文件过大，最大 10MB"}, 413)
        body = self.rfile.read(length)
        blob = None
        if "multipart" in ct:
            boundary = ct.split("boundary=")[1]
            for part in body.split(("--" + boundary).encode()):
                if b"filename=" in part:
                    _, content = part.split(b"\r\n\r\n", 1)
                    content = content.rsplit(b"\r\n", 1)[0]
                    blob = content
                    break
        else:
            blob = body
        if not blob or len(blob) < 100 or blob[:2] != b"PK":
            return self._json({"error": "不是有效的 Word 文档（请选择 .docx 文件）"}, 400)
        upload_dir = os.path.join(CONTENT_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        try:
            page_html, para_count, img_count, media_total = _docx_to_html(blob, upload_dir)
        except Exception as e:
            return self._json({"error": "解析失败：%s" % e}, 500)
        if not page_html.strip():
            return self._json({"error": "文档内容为空"}, 400)
        _log("import-docx", "paras=%d imgs=%d/%d" % (para_count, img_count, media_total))
        return self._json({"ok": True, "html": page_html, "paras": para_count, "imgs": img_count, "media": media_total})

    # ======== SSR: 资讯详情页（SEO 友好，完整 HTML 含 JSON-LD） ========
    def _serve_news(self, news_id):
        item = _read("news/%s.json" % news_id)
        host = self.headers.get("Host", "shop.ywye.top")
        site = "https://" + host
        if not item:
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(NEWS_404_HTML.encode("utf-8"))
            return
        title = item.get("title", "资讯详情")
        category = item.get("category", "资讯")
        date = item.get("date", "")
        # 头条/字节 bytedance 时间标签：用真实发布时间（文件 mtime 精确到秒），兜底取日期 09:00
        try:
            fp = os.path.join(CONTENT_DIR, "news", news_id + ".json")
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
            iso_full = dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        except Exception:
            iso_full = (date + "T09:00:00+08:00") if len(date) == 10 else (date + "+08:00")
        summary = item.get("summary", "") or ""
        settings = _read("settings/site.json") or {}
        phone = settings.get("phone", "158 2526 3079")
        # 封面图 & 默认分享图（正文无封面则用站点默认 og 图）
        # 相对路径补前导 /，以适配 /news/<id> 页面（避免被解析为 /news/assets/...）
        img = (item.get("image", "") or "").strip()
        if img and not img.startswith(("http://", "https://", "/")):
            img = "/" + img
        if img:
            og_image = site + img
            cover_html = ('<img class="article-cover" src="%s" alt="%s" fetchpriority="high" decoding="async" onerror="this.style.display=\'none\'" />'
                          % (html.escape(img), html.escape(title)))
        else:
            og_image = site + "/assets/images/og-image.jpg"
            cover_html = ""
        # 正文：优先 body，缺失则降级展示摘要（内容已写入完整 HTML，无需前端 fetch）
        body = item.get("body", "") or ""
        if body.strip():
            body_html = body
        else:
            body_html = '<p class="article-empty-inline">%s</p>' % html.escape(summary or "正文内容待补充，敬请期待。")
        # 中文日期
        parts = date.split("-")
        date_cn = ("%s 年 %s 月 %s 日" % (parts[0], parts[1], parts[2])) if len(parts) == 3 else date
        # 正文内嵌图片懒加载（封面为首屏 LCP 保持 eager，正文图统一 lazy）
        body_html = re.sub(r'(<img\b)(?![^>]*\bloading=)', r'\1 loading="lazy" decoding="async"', body_html)
        # 相关阅读（同 category 优先，其次按日期降序；取前 4）
        others = [n for n in _list("news") if n["_id"] != news_id]
        others.sort(key=lambda n: n.get("date", "") or "", reverse=True)      # 先按日期降序
        others.sort(key=lambda n: 0 if n.get("category") == category else 1)   # 再按分类稳定排序（同分类在前）
        related = others[:4]
        related_html = ""
        if related:
            cards = []
            for n in related:
                nd = n.get("date", "")
                nday = "-".join(nd.split("-")[1:]) if len(nd.split("-")) == 3 else nd
                cards.append(
                    '<a class="related-card" href="/news/%s">' % html.escape(n["_id"]) +
                    '<div class="rc-date">%s</div>' % html.escape(nday) +
                    '<div class="rc-title">%s</div>' % html.escape(n.get("title", "")) +
                    '<div class="rc-sum">%s</div>' % html.escape(n.get("summary", "")) +
                    '</a>'
                )
            related_html = '<section class="related"><h3>相关阅读</h3><div class="related-grid">%s</div></section>' % "".join(cards)
        # 上一篇 / 下一篇（按日期降序：上一篇=更新，下一篇=更旧）
        all_news = sorted(_list("news"), key=lambda n: n.get("date", "") or "", reverse=True)
        idx = next((i for i, n in enumerate(all_news) if n["_id"] == news_id), -1)
        prev_item = all_news[idx - 1] if idx > 0 else None
        next_item = all_news[idx + 1] if 0 <= idx < len(all_news) - 1 else None
        def _pager_link(label, n):
            if not n:
                return '<span class="pager-item pager-disabled"><span class="pager-label">%s</span></span>' % label
            return ('<a class="pager-item" href="/news/%s"><span class="pager-label">%s</span>'
                    '<span class="pager-title">%s</span></a>'
                    % (html.escape(n["_id"]), label, html.escape(n.get("title", ""))))
        prevnext_html = ('<nav class="article-pager" aria-label="文章导航">%s%s</nav>'
                         % (_pager_link("上一篇", prev_item), _pager_link("下一篇", next_item)))
        # 分享链接（微博 / QQ空间 走 URL 分享；微信走二维码扫码；另备复制链接）
        share_url = site + "/news/" + news_id
        weibo = "https://service.weibo.com/share/share.php?url=%s&title=%s" % (quote(share_url, safe=""), quote(title, safe=""))
        qzone = "https://sns.qzone.qq.com/cgi-bin/qzshare/cgi_qzshare_onekey?url=%s&title=%s" % (quote(share_url, safe=""), quote(title, safe=""))
        qr_api = "https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=0&data=" + quote(share_url, safe="")
        share_html = ('<div class="article-share"><span>分享到：</span>'
                      '<a class="share-btn" href="%s" target="_blank" rel="noopener">微博</a>'
                      '<a class="share-btn" href="%s" target="_blank" rel="noopener">QQ空间</a>'
                      '<button class="share-btn" id="wxShareBtn" type="button">微信</button>'
                      '<button class="share-btn" id="copyLinkBtn" type="button">复制链接</button></div>'
                      '<div class="wx-modal" id="wxModal" role="dialog" aria-modal="true" aria-label="微信分享">'
                      '<div class="wx-modal-box">'
                      '<button class="wx-close" id="wxClose" type="button" aria-label="关闭">&times;</button>'
                      '<p class="wx-tip">打开微信「扫一扫」，分享给好友或朋友圈</p>'
                      '<img class="wx-qr" id="wxQr" src="%s" alt="微信扫码分享" />'
                      '<p class="wx-fallback" id="wxFallback" style="display:none;">二维码加载失败，请点下方「复制链接」后到微信粘贴分享</p>'
                      '<button class="share-btn" id="copyLinkBtn2" type="button">复制链接</button>'
                      '</div></div>'
                      % (weibo, qzone, qr_api))
        # JSON-LD（NewsArticle + BreadcrumbList，提升 AI 收录与引用率）
        jsonld = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "NewsArticle",
                    "headline": title,
                    "image": [og_image],
                    "datePublished": date,
                    "dateModified": date,
                    "author": {"@type": "Organization", "name": "星棠化妆培训学校"},
                    "publisher": {
                        "@type": "Organization",
                        "name": "星棠化妆培训学校",
                        "logo": {"@type": "ImageObject", "url": site + "/assets/images/logo.png"}
                    },
                    "description": summary,
                    "mainEntityOfPage": {"@type": "WebPage", "@id": site + "/news/" + news_id}
                },
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "星棠化妆培训学校", "item": site + "/"},
                        {"@type": "ListItem", "position": 2, "name": "资讯动态", "item": site + "/#studio"},
                        {"@type": "ListItem", "position": 3, "name": title, "item": site + "/news/" + news_id}
                    ]
                }
            ]
        }
        page = (NEWS_PAGE_TPL
                .replace("__TITLE__", html.escape(title))
                .replace("__SUMMARY__", html.escape(summary))
                .replace("__OG_URL__", site + "/news/" + news_id)
                .replace("__OG_IMAGE__", og_image)
                .replace("__DATE_ISO__", date)
                .replace("__DATE_DISPLAY__", html.escape(date_cn))
                .replace("__BYTE_PUBLISHED__", iso_full)
                .replace("__BYTE_LRDATE__", iso_full)
                .replace("__BYTE_UPDATED__", iso_full)
                .replace("__CAT__", html.escape(category))
                .replace("__COVER__", cover_html)
                .replace("__BODY__", body_html)
                .replace("__SHARE__", share_html)
                .replace("__PREVNEXT__", prevnext_html)
                .replace("__RELATED__", related_html)
                .replace("__PHONE__", html.escape(phone))
                .replace("__JSONLD__", json.dumps(jsonld, ensure_ascii=False)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def log_message(self, *a): pass

if __name__ == "__main__":
    # 只监听本机回环，由 Nginx 反向代理对外提供，避免端口直接暴露公网
    HTTPServer(("127.0.0.1",8081), CMS).serve_forever()
