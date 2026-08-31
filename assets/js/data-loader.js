/* =========================================================
   data-loader.js — CMS → 网站 数据桥接（动态渲染版）
   从 /api/public 拉取全部内容，动态生成 DOM
   后台增删内容后，刷新页面即生效
   ========================================================= */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.from(document.querySelectorAll(s)); };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ========== 站点设置 ==========
  function renderSettings(d) {
    if (!d) return;
    var phone = d.phone || '158 2526 3079';
    $$('.hotline b, .cta-phone b, .foot-hot b').forEach(function (el) {
      el.textContent = phone;
    });
    var sloganEl = $('.foot-slogan');
    if (sloganEl) sloganEl.textContent = d.slogan || '以技术为根 · 以审美为魂';
    // 统计数字（HTML 顺序：师资/校区/就业率/课程）
    var order = [d.teacher_count, d.campus_count, d.employment_rate, d.course_count];
    $$('.stat-item .countup').forEach(function (el, i) {
      if (order[i] === undefined || order[i] === null) return;
      el.setAttribute('data-target', String(order[i]));
    });
  }

  // ========== 轮播 ==========
  function renderBanners(banners) {
    var wrap = $('#bannerSwiper .swiper-wrapper');
    if (!wrap || !banners.length) return;
    wrap.innerHTML = banners.map(function (b) {
      var img = b.image ? " style=\"background-image:url('" + esc(b.image) + "')\"" : '';
      return '<div class="swiper-slide slide"' + img + '>' +
        '<div class="slide-deco"></div>' +
        '<div class="slide-inner">' +
        '<p class="slide-en">' + esc(b.title_en) + '</p>' +
        '<h2 class="slide-cn">' + esc(b.title_cn) + '</h2>' +
        '<p class="slide-sub">' + esc(b.subtitle) + '</p>' +
        '<a href="' + esc(b.link_url || '#recruit') + '" class="slide-cta">' + esc(b.link_text || '了解更多') + '</a>' +
        '</div></div>';
    }).join('');
  }

  // ========== 课程（双轮播联动） ==========
  function renderCourses(courses) {
    var topWrap = $('#galleryTop .swiper-wrapper');
    var thumbWrap = $('#galleryThumbs .swiper-wrapper');
    if (!topWrap || !thumbWrap || !courses.length) return;
    topWrap.innerHTML = courses.map(function (c) {
      var img = c.image ? " style=\"background-image:url('" + esc(c.image) + "')\"" : '';
      return '<div class="swiper-slide"' + img + '>' +
        '<div class="course-detail">' +
        '<div class="course-detail-ico">' + esc(c.icon) + '</div>' +
        '<h4>' + esc(c.title) + '</h4>' +
        '<p>' + esc(c.description) + '</p>' +
        '</div></div>';
    }).join('');
    thumbWrap.innerHTML = courses.map(function (c) {
      return '<div class="swiper-slide"><span class="thumb-tab">' + esc(c.title) + '</span></div>';
    }).join('');
  }

  // ========== 新闻（分页：每页 6 条，最新在前） ==========
  var newsState = { list: [], page: 1, perPage: 6 };

  function newsCardHtml(n) {
    var day = '', ym = '';
    if (n.date) {
      var p = String(n.date).split('-');
      if (p.length === 3) { day = p[2]; ym = p[0] + '.' + p[1]; }
    }
    var cat = n.category || '资讯';
    return '<a class="news-card cms-reveal" href="/news/' + esc(n._id) + '" target="_blank" rel="noopener" data-category="' + esc(cat) + '">' +
      '<span class="news-card-date"><b>' + esc(day) + '</b><em>' + esc(ym) + '</em></span>' +
      '<h4>' + esc(n.title) + '</h4>' +
      '<p>' + esc(n.summary) + '</p>' +
      '</a>';
  }

  function renderNewsPage() {
    var list = $('#newslist');
    if (!list) return;
    var total = newsState.list.length;
    var totalPages = Math.max(1, Math.ceil(total / newsState.perPage));
    if (newsState.page < 1) newsState.page = 1;
    if (newsState.page > totalPages) newsState.page = totalPages;
    var start = (newsState.page - 1) * newsState.perPage;
    list.innerHTML = newsState.list.slice(start, start + newsState.perPage).map(newsCardHtml).join('');
    var pager = $('#newsPager');
    if (pager) {
      if (totalPages <= 1) {
        pager.style.display = 'none';
      } else {
        pager.style.display = 'flex';
        var h = '<button type="button" class="pg-btn" data-page="' + (newsState.page - 1) + '"' + (newsState.page <= 1 ? ' disabled' : '') + '>上一页</button>';
        for (var i = 1; i <= totalPages; i++) {
          h += '<button type="button" class="pg-btn' + (i === newsState.page ? ' active' : '') + '" data-page="' + i + '">' + i + '</button>';
        }
        h += '<button type="button" class="pg-btn" data-page="' + (newsState.page + 1) + '"' + (newsState.page >= totalPages ? ' disabled' : '') + '>下一页</button>';
        pager.innerHTML = h;
      }
    }
  }

  function renderNews(news) {
    var list = $('#newslist');
    if (!list || !news || !news.length) return;
    // 按日期倒序（最新在前）
    newsState.list = news.slice().sort(function (a, b) {
      return String(b.date || '').localeCompare(String(a.date || ''));
    });
    newsState.page = 1;
    renderNewsPage();
  }

  // 分页点击（事件委托）
  document.addEventListener('click', function (e) {
    var btn = e.target && e.target.closest ? e.target.closest('#newsPager .pg-btn') : null;
    if (!btn || btn.disabled) return;
    var page = parseInt(btn.getAttribute('data-page'), 10);
    if (!page) return;
    newsState.page = page;
    renderNewsPage();
  });

  // ========== 城市 ==========
  function renderCities(cities) {
    var grid = $('.city-grid');
    if (!grid || !cities.length) return;
    grid.innerHTML = cities.map(function (c, i) {
      var img = c.image ? " style=\"background-image:url('" + esc(c.image) + "')\"" : '';
      return '<a class="city-card cms-reveal" href="#recruit"' + img + '>' +
        '<span class="city-name">' + esc(c.name) + '</span>' +
        '<span class="city-en">' + esc(c.name_en) + '</span>' +
        '</a>';
    }).join('');
  }

  // ========== 启动 ==========
  function boot() {
    fetch('/api/public')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        renderSettings(d.settings);
        renderBanners(d.banners || []);
        renderCourses(d.courses || []);
        renderNews(d.news || []);
        renderCities(d.cities || []);
        // 通知 main.js：数据已写入 DOM，可以安全初始化 Swiper
        window.__cmsReady = true;
        window.dispatchEvent(new CustomEvent('cms:ready'));
      })
      .catch(function () {
        // 接口失败时保留 HTML 硬编码默认内容
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
