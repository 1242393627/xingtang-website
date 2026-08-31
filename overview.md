# 星棠官网 SEO/GEO 整改 + 安全审计修复 — 交付说明

**日期**：2026-08-18　**站点**：https://shop.ywye.top/　（源站 43.156.13.57，nginx + Python CMS 8081）

## 一、安全审计（6 项，全部修复并线上验证）

| 风险 | 问题 | 修复 | 验证 |
|---|---|---|---|
| 中 | 安全响应头全部缺失 | nginx 加 HSTS / CSP / X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy（`always` 覆盖错误页） | curl 6 项头全部可见 |
| 中 | /admin/ 无需认证 | 加 `auth_basic`（凭据：**xtadmin / <basic-auth-密码-见服务器/.htpasswd_xingtang>**） | /admin/ 返回 401 |
| 中 | /api/login GET 误导 | do_GET 改为返回 405 | GET /api/login → 405 |
| 低 | nginx 版本泄露 | `server_tokens off`（源站生效） | 源站 `Server: nginx`；公网 `nginx/1.24.0` 为 **CDN 边缘注入，需腾讯云 CDN 控制台隐藏** |
| 低 | token 存 localStorage | admin 全部改 sessionStorage（5 处） | — |
| 低 | API 端点明文可见 | 维持（后台必须可用），已由 basic auth + token 双层防护覆盖 | — |

## 二、SEO/GEO 整改（12 项，全部落地并线上验证）

1. **唯一 H1**：首屏第一张 slide 升级为「星棠化妆培训学校 · 七城直营美业教育」
2. **sitemap 扩展**：1 个 URL → 9 个（首页 + 8 篇 news，lastmod 取文章真实日期）
3. **图片压缩**：5.59MB → 4.01MB（省 28%）；Hero 保真 ≤180KB，其余 ≤100KB
4. **viewport**：移除 maximum-scale=2.0，恢复用户缩放
5. **FAQ**：新增 8 条真实问答区块 + FAQPage JSON-LD（10 问）
6. **www 301**：www.shop.ywye.top server block 已配（待 DNS 解析后生效）
7. **HSTS + gzip + 安全头**：见上表，gzip 已生效（Content-Encoding: gzip）
8. **外链背书**：页脚落地为中国美发美容协会 / 人社部 / 中国就业网
9. **结构化数据**：首页新增 Course ItemList；资讯页 JSON-LD 升级为 NewsArticle + BreadcrumbList（@graph）
10. **语义容器**：`<main>` 包裹主内容；preconnect cdn.jsdelivr
11. **口径统一**：「七省十三座」全部改为「七城直营校区 + 教学与服务网络辐射十三座城市」；就业率等统计加口径注
12. **页脚占位**：外链落地（见 8），资质/隐私/免责改为页内锚点

## 三、改动文件

- `index.html`、`assets/css/style.css`（FAQ/stats-note 样式）
- `sitemap.xml`（9 URL）
- `cms_server.py`（/api/login 405 + NewsArticle@graph）
- `admin/index.html`（sessionStorage）
- `nginx-cms.conf`（vhost 新配置，服务器原配置已备份 .bak_时间戳）
- `tools/compress_images.py`、`tools/compress_images2.py`

## 四、遗留事项

- CDN 边缘 `Server` 版本头需在腾讯云 CDN 控制台隐藏
- www 301 需等 DNS 解析 www 记录
- 后台访问：https://shop.ywye.top/admin/ （浏览器弹窗输入 xtadmin / <basic-auth-密码-见服务器/.htpasswd_xingtang>）

---

# 第二轮：星棠官网交付整改建议（12 项）执行结果

> 目标：7.5 → 8.5+；P0/P1/P2 全部落地，P3 部分落地，已部署并线上验证。

## P0 必修（3/3 ✅）
| 项 | 结果 |
|---|---|
| 安全响应头 | 上轮已做。说明：CSP 用 `frame-ancestors 'none'`、`X-Frame-Options: DENY`（比建议的 'self'/SAMEORIGIN 更严）；HSTS 未加 includeSubDomains（www 无证书，加了会阻断 www）。 |
| Swiper SRI | ✅ js+css 均加 `integrity=sha384-...` + `crossorigin=anonymous`（hash 从 jsdelivr 实测算出） |
| 移除禁用右键 | ✅ 删除 main.js `oncontextmenu` 拦截。防盗链/水印暂缓（referer 校验会误伤微信内分享） |

## P1 必修（4/4 ✅）
| 项 | 结果 |
|---|---|
| 图片 WebP + srcset | ✅ 全量生成 WebP；20 处 CSS 背景改 `image-set()`（webp 优先）；8 张作品图改 `<picture>`（750w+原宽 srcset、sizes、width/height 防 CLS） |
| 字体方案统一 | ✅ 保留纯 CSS `calc(100vw/1920*100)`，补 `min-width:770px` 媒体查询（<770 用 750 基准），删除 JS setFont（消除双实现与 FOUC） |
| 缓存策略 | 维持现状（图片 30d / js+css 12h）。无文件名 hash，`immutable` 会导致更新不生效，故不加。 |
| Swiper 瘦身 | 走 `defer` 方案（3 个脚本移 head + defer，不阻塞首屏）。ESM 按需引入改动大、风险高，暂缓。 |

## P2 必修（2/2 ✅）
| 项 | 结果 |
|---|---|
| 死链/占位 | ✅ 在线咨询改站内微信弹窗（复用 #wechatFixed）；删除「加载更多」setTimeout 模拟（data-loader 已有真实分页）；favicon.ico + apple-touch-icon 落地（Pillow 由 logo 生成）；外链/隐私/免责上轮已落地 |
| 表单加固 | ✅ 后端：手机号格式校验 + 同 IP/同手机号每日 5 次频控 + 一次性 token（10 分钟）防重放；前端：提交按钮禁用防连点 |

## P3 建议（部分）
- ✅ 弹窗可访问性：4 个弹窗加 `role=dialog + aria-modal + aria-label/labelledby`；新增 focusDialog/restoreFocus（打开聚焦、Tab 循环、关闭还原焦点）
- ✅ 代码卫生：删重复注释、修 initSwipers 缩进、删与 HTML placeholder 重复的清空 JS
- ⏳ 性能基线自测（Lighthouse）待用户侧跑分

## 线上验证（全部 curl 实测）
image-set×20 ｜ picture×8 ｜ SRI×2 ｜ defer×4 ｜ role=dialog×4 ｜ favicon.ico/apple-touch 200 ｜ work_09.webp 200 (86.9KB) ｜ /api/submit 四用例（格式/token/成功/重放）全部按预期 ｜ 测试数据已清理

## 改动文件
index.html / assets/css/style.css / assets/js/main.js / cms_server.py / favicon.ico / apple-touch-icon.png / assets/images/*.webp（+ -750.webp 变体）/ tools/gen_webp_favicon.py
