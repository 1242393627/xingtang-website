/* =========================================================
   星棠官网 · 主站交互脚本
   功能包含 Swiper/Coverflow/CountUp/弹窗/LazyLoad
   依赖 Swiper 11 CDN
   ========================================================= */
(function () {
  'use strict';
  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  /* 弹窗焦点管理（可访问性）：打开聚焦、Tab 循环、关闭还原焦点 */
  var lastFocus = null;
  function focusDialog(dialog, trigger) {
    lastFocus = trigger || lastFocus;
    var focusables = dialog.querySelectorAll('a[href], button, input, textarea, select, [tabindex]:not([tabindex="-1"])');
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    if (first) first.focus();
    dialog.addEventListener('keydown', function trap(e) {
      if (e.key !== 'Tab') return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); if (last) last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); if (first) first.focus();
      }
    });
  }
  function restoreFocus(trigger) {
    var t = trigger || lastFocus;
    if (t && t.focus) { try { t.focus(); } catch (e) {} }
  }

  /* =========================================================
     1. Swiper: Banner 轮播（对标 our-swiper）
     ========================================================= */
  var bannerSwiper = null;
  var galleryThumbs = null;
  var galleryTop = null;

  // Swiper 统一在 CMS 数据就绪后初始化，避免轮播在空容器上初始化导致空白
  function initSwipers() {
    // 销毁已有实例，保证重复触发（事件 + 兜底）时不会叠加
    if (bannerSwiper) { try { bannerSwiper.destroy(true, true); } catch (e) {} bannerSwiper = null; }
    if (galleryThumbs) { try { galleryThumbs.destroy(true, true); } catch (e) {} galleryThumbs = null; }
    if (galleryTop) { try { galleryTop.destroy(true, true); } catch (e) {} galleryTop = null; }

    if ($('#bannerSwiper')) {
      bannerSwiper = new Swiper('#bannerSwiper', {
        slidesPerView: 1,
        loop: true,
        speed: 1000,
        autoplay: { delay: 5000, disableOnInteraction: false },
        pagination: { el: '.swiper-pagination', clickable: true },
        navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
        observer: true,
        observeParents: true,
      });
      // hover 暂停
      var bannerEl = $('.banner');
      if (bannerEl) {
        bannerEl.addEventListener('mouseenter', function () { bannerSwiper.autoplay.stop(); });
        bannerEl.addEventListener('mouseleave', function () { bannerSwiper.autoplay.start(); });
      }
      // 标签页隐藏暂停
      document.addEventListener('visibilitychange', function () {
        if (!bannerSwiper) return;
        if (document.hidden) bannerSwiper.autoplay.stop();
        else bannerSwiper.autoplay.start();
      });
    }

    /* =========================================================
       4. Swiper: 学员作品 Coverflow（对标 excellent-list）
       ========================================================= */
    if ($('#worksSwiper')) {
      new Swiper('#worksSwiper', {
        effect: 'coverflow',
        grabCursor: true,
        centeredSlides: true,
        slidesPerView: 1.8,
        loop: true,
        lazy: { loadPrevNext: true },
        coverflowEffect: {
          rotate: 0,
          stretch: 200,
          depth: 40,
          modifier: 1,
        },
        breakpoints: {
          767: { slidesPerView: 1.6, coverflowEffect: { stretch: 80, depth: 50, modifier: 2 } },
          400: { slidesPerView: 1.4, coverflowEffect: { stretch: 60, depth: 30, modifier: 2 } },
        },
      });
    }

    /* =========================================================
       5. Swiper: 课程双轮播联动（对标 gallery-top + gallery-thumbs）
       ========================================================= */
    if ($('#galleryTop')) {
      galleryThumbs = new Swiper('#galleryThumbs', {
        slidesPerView: 6,
        centeredSlides: true,
        slideToClickedSlide: true,
        watchSlidesProgress: true,
        speed: 600,
        observer: true,
        observeParents: true,
        breakpoints: {
          900: { slidesPerView: 'auto', centeredSlides: false, watchSlidesProgress: true },
          600: { slidesPerView: 3.5 },
          400: { slidesPerView: 2.8 },
        },
      });
      galleryTop = new Swiper('#galleryTop', {
        slidesPerView: 1,
        speed: 600,
        slideToClickedSlide: true,
        autoHeight: false,
        observer: true,
        observeParents: true,
        thumbs: { swiper: galleryThumbs },
      });
    }
  }

  // 数据就绪后再初始化 Swiper（data-loader.js 拉取 /api/public 完成后触发）
  window.addEventListener('cms:ready', initSwipers);
  if (window.__cmsReady) initSwipers();

  /* =========================================================
     6. 头部 Sticky（对标 $(document).scroll → .fixed）
     ========================================================= */
  (function headerSticky() {
    var pcheader = $('.pcheader');
    if (!pcheader) return;
    function check() {
      var top = window.pageYOffset || document.documentElement.scrollTop;
      pcheader.classList.toggle('fixed', top > 10);
    }
    window.addEventListener('scroll', check, { passive: true });
    check();
  })();

  /* =========================================================
     7. CountUp 数字滚动（对标 CountUp.js）
     ========================================================= */
  function initCountUp() {
    var counters = $$('.countup');
    if (counters.length === 0) return;
    var triggered = false;
    function trigger() {
      if (triggered) return;
      var statsEl = $('#stats');
      if (!statsEl) return;
      var rect = statsEl.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.8) {
        triggered = true;
        counters.forEach(function (el) {
          var target = parseInt(el.getAttribute('data-target'), 10) || 0;
          var start = 0;
          var duration = 1800;
          var stepTime = 20;
          var steps = duration / stepTime;
          var increment = target / steps;
          var current = 0;
          var timer = setInterval(function () {
            current += increment;
            if (current >= target) {
              el.textContent = target;
              clearInterval(timer);
            } else {
              el.textContent = Math.floor(current);
            }
          }, stepTime);
        });
      }
    }
    window.addEventListener('scroll', trigger, { passive: true });
    trigger();
  }
  initCountUp();

  /* =========================================================
     8. WOW 动画 + 滚动入场（对标 WOW.js + scrollAnimation2）
     ========================================================= */
  function initScrollAnimations() {
    /* 8a. WOW 类元素 */
    var wowEls = $$('.wow');
    if (wowEls.length > 0) {
      var wowObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var el = entry.target;
            var delay = el.getAttribute('data-wow-delay') || '0s';
            el.style.animationDelay = delay;
            el.classList.add('animate__animated');
            var animClass = Array.from(el.classList).find(function (c) { return c.indexOf('fadeIn') === 0; }) || 'fadeInUp';
            el.classList.add(animClass);
            wowObserver.unobserve(el);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
      wowEls.forEach(function (el) { wowObserver.observe(el); });
    }

    /* 8b. .section-animate 通用入场（对标 .secwen → .animate） */
    var sectionEls = $$('.section-animate');
    if (sectionEls.length > 0) {
      var sectionObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate');
            // 移除 loading-sw（对标 _this.find(".loading-sw").remove()）
            var loader = entry.target.querySelector('.loading-sw');
            if (loader) loader.remove();
            sectionObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });
      sectionEls.forEach(function (el) { sectionObserver.observe(el); });
    }
  }
  initScrollAnimations();

  /* =========================================================
     9. 全屏菜单（对标 menu-fixed）
     ========================================================= */
  (function menuFixed() {
    var menuToggle = $('#menuToggle');
    var menuFixed = $('#menuFixed');
    var menuClose = $('#menuFixedClose');
    var body = document.body;

    function openMenu() {
      if (menuFixed) menuFixed.classList.add('active');
      body.classList.add('on');
    }
    function closeMenu() {
      if (menuFixed) menuFixed.classList.remove('active');
      body.classList.remove('on');
    }
    if (menuToggle) {
      menuToggle.addEventListener('mouseenter', openMenu);
      menuToggle.addEventListener('click', openMenu);
    }
    if (menuClose) menuClose.addEventListener('click', closeMenu);
    if (menuFixed) {
      menuFixed.addEventListener('mouseleave', closeMenu);
      menuFixed.addEventListener('click', function (e) {
        if (e.target === menuFixed) closeMenu();
      });
    }
    // 菜单内链接点击关闭
    $$('.menu-fixed-nav a').forEach(function (a) {
      a.addEventListener('click', closeMenu);
    });
  })();

  /* =========================================================
     10. 搜索遮罩（对标 search-dialog）
     ========================================================= */
  (function search() {
    var btn = $('#searchBtn');
    var alert = $('#searchAlert');
    var close = $('#searchClose');
    var form = $('#searchForm');
    if (!btn || !alert) return;
    // 结果容器（懒创建）
    var resultsBox = null;
    function ensureResults() {
      if (!resultsBox) {
        resultsBox = document.createElement('div');
        resultsBox.className = 'search-results';
        var inp = $('.search-input', alert);
        if (inp && inp.parentNode) inp.parentNode.appendChild(resultsBox);
      }
      return resultsBox;
    }
    function open() {
      alert.classList.add('active');
      focusDialog(alert, btn);
      var inp = $('.search-input', alert);
      if (inp) setTimeout(function () { inp.focus(); }, 100);
    }
    function hide() {
      alert.classList.remove('active');
      restoreFocus(btn);
      var inp = $('.search-input', alert);
      if (inp) inp.value = '';
      if (resultsBox) resultsBox.innerHTML = '';
    }
    btn.addEventListener('click', open);
    if (close) close.addEventListener('click', hide);
    alert.addEventListener('click', function (e) { if (e.target === alert) hide(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });

    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var inp = $('.search-input', alert);
        var q = (inp ? inp.value : '').trim();
        if (!q) return;
        var box = ensureResults();
        box.innerHTML = '<p class="search-hint">搜索中…</p>';
        fetch('/api/public').then(function (r) { return r.json(); }).then(function (d) {
          var results = [];
          (d.courses || []).forEach(function (c) {
            if ((c.title + ' ' + (c.description || '')).indexOf(q) >= 0) {
              results.push({type:'课程', title:c.title, anchor:'#courses'});
            }
          });
          (d.news || []).forEach(function (n) {
            if ((n.title + ' ' + (n.summary || '')).indexOf(q) >= 0) {
              results.push({type:'资讯', title:n.title, anchor:'#studio'});
            }
          });
          (d.cities || []).forEach(function (c) {
            if ((c.name + ' ' + (c.name_en || '')).indexOf(q) >= 0) {
              results.push({type:'校区', title:c.name + '（' + c.name_en + '）', anchor:'#env'});
            }
          });
          (d.banners || []).forEach(function (b) {
            if ((b.title_cn + ' ' + (b.subtitle || '')).indexOf(q) >= 0) {
              results.push({type:'专题', title:b.title_cn, anchor:'#home'});
            }
          });
          if (!results.length) {
            box.innerHTML = '<p class="search-hint">没有找到匹配"' + escHtml(q) + '"的内容</p>';
            return;
          }
          box.innerHTML = results.slice(0, 12).map(function (r) {
            return '<a class="search-item" href="' + r.anchor + '">' +
              '<span class="search-tag">' + r.type + '</span>' +
              '<span class="search-title">' + escHtml(r.title) + '</span>' +
              '</a>';
          }).join('') + (results.length > 12 ? '<p class="search-hint">还有 ' + (results.length - 12) + ' 条结果</p>' : '');
          // 点击跳转关闭弹窗
          $$('.search-item', box).forEach(function (a) {
            a.addEventListener('click', function () { setTimeout(hide, 100); });
          });
        }).catch(function () {
          box.innerHTML = '<p class="search-hint">搜索失败，请稍后重试</p>';
        });
      });
    }
    function escHtml(s) { return String(s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  })();

  /* =========================================================
     9b. 分享按钮（navigator.share / 复制链接）
     ========================================================= */
  (function share() {
    var btn = $('.sidebar-share');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var data = { title: document.title, url: window.location.href };
      if (navigator.share) {
        navigator.share(data).catch(function () {});
      } else if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(data.url).then(function () {
          var t = document.createElement('div');
          t.className = 'msg show ok';
          t.textContent = '链接已复制';
          document.body.appendChild(t);
          setTimeout(function () { t.remove(); }, 2000);
        });
      }
    });
  })();

  /* =========================================================
     10b. 微信弹窗（复制微信号）
     ========================================================= */
  (function wechatPop() {
    var btn = document.querySelector('.icon-btn.wechat');
    var box = $('#wechatFixed');
    var close = $('#wechatClose');
    var copy = $('#wechatCopy');
    var tip = $('#wechatTip');
    var wechatId = '15825263079';
    if (!box) return;
    function open() {
      box.style.display = 'flex';
      focusDialog(box, btn);
    }
    function hide() {
      box.style.display = 'none';
      restoreFocus(btn);
    }
    if (btn) btn.addEventListener('click', open);
    if (close) close.addEventListener('click', hide);
    box.addEventListener('click', function (e) { if (e.target === box) hide(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
    // 供「在线咨询」等按钮复用
    window.XT_openWechat = open;
    window.XT_closeWechat = hide;
    if (copy) {
      copy.addEventListener('click', function () {
        function fallback() {
          var ta = document.createElement('textarea');
          ta.value = wechatId;
          ta.style.position = 'fixed'; ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand('copy'); tip.textContent = '微信号已复制'; }
          catch (err) { tip.textContent = '微信号：' + wechatId; }
          document.body.removeChild(ta);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(wechatId).then(function () {
            tip.textContent = '微信号已复制，去微信粘贴添加';
          }).catch(fallback);
        } else {
          fallback();
        }
      });
    }
  })();

  /* =========================================================
     11. 移动端菜单（对标 m-header .nav-btn）
     ========================================================= */
  (function mobileNav() {
    var toggle = $('#menuToggle');
    var mBtn = $('#mobileMenuBtn');
    var mask = $('#mobileMask');
    var body = document.body;

    function closeNav() { body.classList.remove('nav-open'); }
    function toggleNav() { body.classList.toggle('nav-open'); }

    if (toggle) {
      toggle.addEventListener('click', function () {
        if (window.innerWidth <= 767) toggleNav();
      });
    }
    if (mBtn) {
      mBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        toggleNav();
      });
    }
    if (mask) mask.addEventListener('click', closeNav);

    // 移动端下拉菜单手风琴
    $$('.nav-item.has-drop > a').forEach(function (a) {
      a.addEventListener('click', function (e) {
        if (window.innerWidth <= 767) {
          e.preventDefault();
          var item = a.parentElement;
          item.classList.toggle('open');
        }
      });
    });

    // 非下拉链接点击关闭菜单
    $$('.nav-list a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (a.parentElement.classList.contains('has-drop')) return;
        closeNav();
      });
    });
  })();

  /* =========================================================
     12. 回到顶部
     ========================================================= */
  var toTopBtn = $('#toTop');
  if (toTopBtn) {
    toTopBtn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* =========================================================
     13. 锚点平滑滚动（对标 visual_button_scroll_down）
     ========================================================= */
  (function smoothScroll() {
    $$('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        if (a.parentElement && a.parentElement.classList.contains('has-drop')) return;
        var href = a.getAttribute('href');
        if (!href || href === '#') return;
        var target = $(href);
        if (!target) return;
        e.preventDefault();
        var offset = 120;
        var targetPos = target.getBoundingClientRect().top + window.pageYOffset - offset;
        var startPos = window.pageYOffset;
        var distance = targetPos - startPos;
        var duration = 1200;
        var startTime = null;
        function easeInOutQuad(t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; }
        function animate(currentTime) {
          if (!startTime) startTime = currentTime;
          var elapsed = currentTime - startTime;
          var progress = Math.min(elapsed / duration, 1);
          window.scrollTo(0, startPos + distance * easeInOutQuad(progress));
          if (progress < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
      });
    });
  })();

  /* =========================================================
     14. 视频弹窗（对标 clickVideo）
     ========================================================= */
  (function videoPopup() {
    var videoFixed = $('#videoFixed');
    var videoPlayer = $('#videoPlayer');
    var videoClose = $('#videoClose');
    var videoBox = $('#videoBox');

    function openVideo(src) {
      if (!videoFixed || !videoPlayer) return;
      videoPlayer.setAttribute('src', src);
      videoFixed.style.display = 'flex';
      focusDialog(videoFixed);
    }
    function closeVideo() {
      if (!videoFixed || !videoPlayer) return;
      videoPlayer.setAttribute('src', '');
      videoFixed.style.display = 'none';
      restoreFocus();
    }
    if (videoClose) videoClose.addEventListener('click', closeVideo);
    if (videoFixed) {
      videoFixed.addEventListener('click', function (e) {
        if (e.target === videoFixed) closeVideo();
      });
    }
    if (videoBox) {
      videoBox.addEventListener('click', function (e) { e.stopPropagation(); });
    }
    // 暴露到全局
    window.clickVideo = function (selector) {
      var el = typeof selector === 'string' ? $(selector) : selector;
      if (!el) return;
      el.addEventListener('click', function () {
        var src = el.getAttribute('data-src');
        if (src) openVideo(src);
      });
    };
  })();

  /* =========================================================
     15. 招生 CTA 表单
     ========================================================= */
  (function lazyLoad() {
    if (!('IntersectionObserver' in window)) return;
    var lazyImgs = $$('img[loading="lazy"]');
    if (lazyImgs.length === 0) return;
    var lazyObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
          }
          lazyObserver.unobserve(img);
        }
      });
    }, { rootMargin: '200px 0px' });
    lazyImgs.forEach(function (img) { lazyObserver.observe(img); });
  })();

  /* =========================================================
     17. 招生 CTA 表单（含防连点与一次性提交 token）
     ========================================================= */
  (function ctaForm() {
    var form = $('#ctaForm');
    var tip = $('#ctaTip');
    if (!form) return;
    var submitBtn = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var nameInput = form.querySelector('input[name="name"]');
      var phoneInput = form.querySelector('input[name="phone"]');
      var name = nameInput ? nameInput.value : '';
      var phone = phoneInput ? phoneInput.value : '';
      if (name.trim() === '' || phone.trim() === '') {
        if (tip) tip.textContent = '请填写称呼与联系电话';
        return;
      }
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = '提交中…'; }
      if (tip) tip.textContent = '提交中...';
      var token = 't' + Date.now() + Math.random().toString(36).slice(2, 8);
      fetch('/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, phone: phone, t: token })
      }).then(function (r) { return r.json(); })
        .then(function (d) {
          if (tip) tip.textContent = d.msg || '提交成功！课程顾问将尽快与您联系';
          form.reset();
        })
        .catch(function () {
          if (tip) tip.textContent = '网络异常，请稍后重试';
        })
        .finally(function () {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = '免费咨询'; }
        });
    });
  })();

  /* =========================================================
     18. 在线咨询按钮（站内微信弹窗）
     ========================================================= */
  var chatBtn = $('#onlineChat');
  if (chatBtn) {
    chatBtn.addEventListener('click', function () {
      if (window.XT_openWechat) window.XT_openWechat();
      else window.open('https://work.weixin.qq.com/', '_blank');
    });
  }
})();