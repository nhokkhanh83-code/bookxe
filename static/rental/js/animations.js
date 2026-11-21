/* ==========================================================================
   BOOKXE — ANIMATION & INTERACTION CONTROLLER
   Tự động áp dụng hiệu ứng cho nội dung tĩnh lẫn nội dung tạo động bằng AJAX.
   Không can thiệp vào logic nghiệp vụ của trang.
   ========================================================================== */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  /* ------------------------------------------------------------------ *
   * 1. SCROLL REVEAL — hé lộ element khi cuộn vào viewport
   * ------------------------------------------------------------------ */
  var revealObserver = null;
  var REVEAL_SELECTOR = [
    '.bx-shop-card', '.bx-vehicle-card', '.bx-blog-card',
    '.bx-stat-card', '.bx-section-title', '.bx-display',
    '.bx-shop-hero', '.bx-detail-main-img', '.bx-spec-box'
  ].join(',');

  function tagReveals(root) {
    if (reduceMotion) return;
    var scope = root || document;
    var nodes = scope.querySelectorAll(REVEAL_SELECTOR);
    nodes.forEach(function (el) {
      if (el.classList.contains('bx-reveal') || el.classList.contains('bx-in')) return;
      el.classList.add('bx-reveal');
    });
    // Stagger theo thứ tự trong cùng một hàng/container
    var groups = scope.querySelectorAll('#shopGrid, #featuredVehicleGrid, .row.g-4');
    groups.forEach(function (group) {
      var children = group.querySelectorAll('.bx-reveal:not([style*="--bx-d"])');
      children.forEach(function (child, i) {
        child.style.setProperty('--bx-d', Math.min(i, 7) * 80 + 'ms');
      });
    });
    if (revealObserver) {
      nodes.forEach(function (el) { revealObserver.observe(el); });
    }
  }

  function initReveal() {
    if (reduceMotion || !('IntersectionObserver' in window)) {
      document.querySelectorAll('.bx-reveal').forEach(function (el) {
        el.classList.add('bx-in');
      });
      return;
    }
    revealObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('bx-in');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    tagReveals(document);
    document.querySelectorAll('.bx-reveal').forEach(function (el) {
      revealObserver.observe(el);
    });
    // Fallback: luôn hiện sau 3s nếu observer bị kẹt
    setTimeout(function () {
      document.querySelectorAll('.bx-reveal').forEach(function (el) {
        el.classList.add('bx-force-show');
      });
    }, 3000);
  }

  /* ------------------------------------------------------------------ *
   * 2. MEDIA HOST — tạo vùng hover zoom + nút phóng to cho ảnh
   * ------------------------------------------------------------------ */
  var ZOOM_SELECTOR = [
    '.bx-vehicle-img', '.card-img-top', '.bx-shop-banner img',
    '.bx-detail-main-img', '.bx-hero-art > img'
  ].join(',');
  var zoomSources = []; // { src, alt }

  function makeMediaHost(img) {
    var host = img.parentElement;
    if (!host || host.classList.contains('bx-media-host')) return;

    // Không wrap ảnh là con trực tiếp của thẻ <a> nếu điều đó phá layout:
    // chỉ thêm class + position relative cho parent hiện tại.
    host.classList.add('bx-media-host');
    if (getComputedStyle(host).position === 'static') {
      host.style.position = 'relative';
    }

    // Đăng ký nguồn cho lightbox (loại trùng)
    var src = img.getAttribute('src');
    var alt = img.getAttribute('alt') || '';
    if (src && !zoomSources.some(function (s) { return s.src === src; })) {
      zoomSources.push({ src: src, alt: alt });
    }

    if (host.querySelector('.bx-zoom-btn')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bx-zoom-btn';
    btn.setAttribute('aria-label', 'Phóng to hình ảnh');
    btn.innerHTML = '<i class="bi bi-zoom-in"></i>';
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      openLightbox(src, alt);
    });
    host.appendChild(btn);
  }

  function initMedia() {
    document.querySelectorAll(ZOOM_SELECTOR).forEach(makeMediaHost);
    // Sparkle trang trí cho hero
    var hero = document.querySelector('.bx-hero-art');
    if (hero && !hero.querySelector('.bx-sparkle')) {
      [['8%', '18%', '0s'], ['82%', '72%', '.7s'], ['68%', '10%', '1.4s']].forEach(function (p) {
        var s = document.createElement('i');
        s.className = 'bi bi-stars bx-sparkle';
        s.style.left = p[0];
        s.style.top = p[1];
        s.style.animationDelay = p[2];
        hero.appendChild(s);
      });
    }
  }

  /* ------------------------------------------------------------------ *
   * 3. LIGHTBOX — xem ảnh phóng to, điều hướng bằng nút/phím
   * ------------------------------------------------------------------ */
  var lightbox, lbImage, lbCaption, currentIndex = 0;

  function buildLightbox() {
    if (document.getElementById('bxLightbox')) return;
    lightbox = document.createElement('div');
    lightbox.id = 'bxLightbox';
    lightbox.className = 'bx-lightbox';
    lightbox.setAttribute('role', 'dialog');
    lightbox.setAttribute('aria-modal', 'true');
    lightbox.innerHTML =
      '<button class="bx-lb-close" aria-label="Đóng"><i class="bi bi-x-lg"></i></button>' +
      '<button class="bx-lb-nav bx-lb-prev" aria-label="Ảnh trước"><i class="bi bi-chevron-left"></i></button>' +
      '<img alt="">' +
      '<button class="bx-lb-nav bx-lb-next" aria-label="Ảnh tiếp"><i class="bi bi-chevron-right"></i></button>' +
      '<div class="bx-lb-caption"></div>';
    document.body.appendChild(lightbox);
    lbImage = lightbox.querySelector('img');
    lbCaption = lightbox.querySelector('.bx-lb-caption');

    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox) closeLightbox();
    });
    lightbox.querySelector('.bx-lb-close').addEventListener('click', closeLightbox);
    lightbox.querySelector('.bx-lb-prev').addEventListener('click', function () { stepLightbox(-1); });
    lightbox.querySelector('.bx-lb-next').addEventListener('click', function () { stepLightbox(1); });
    document.addEventListener('keydown', function (e) {
      if (!lightbox.classList.contains('bx-open')) return;
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') stepLightbox(-1);
      if (e.key === 'ArrowRight') stepLightbox(1);
    });
  }

  function openLightbox(src, alt) {
    buildLightbox();
    currentIndex = Math.max(0, zoomSources.findIndex(function (s) { return s.src === src; }));
    renderLightbox();
    lightbox.classList.add('bx-open');
    document.body.classList.add('bx-lb-open');
  }

  function renderLightbox() {
    if (!zoomSources.length) return;
    var item = zoomSources[currentIndex];
    lbImage.src = item.src;
    lbImage.alt = item.alt;
    lbCaption.textContent = item.alt;
    var multi = zoomSources.length > 1;
    lightbox.querySelector('.bx-lb-prev').style.display = multi ? 'flex' : 'none';
    lightbox.querySelector('.bx-lb-next').style.display = multi ? 'flex' : 'none';
  }

  function stepLightbox(dir) {
    if (!zoomSources.length) return;
    currentIndex = (currentIndex + dir + zoomSources.length) % zoomSources.length;
    renderLightbox();
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('bx-open');
    document.body.classList.remove('bx-lb-open');
  }

  /* ------------------------------------------------------------------ *
   * 4. RIPPLE — hiệu ứng lan khi click nút / link điều hướng
   * ------------------------------------------------------------------ */
  function initRipple() {
    if (reduceMotion) return;
    document.addEventListener('click', function (e) {
      var target = e.target.closest('.btn, .quick-city, .bx-zoom-btn, .nav-link');
      if (!target) return;
      if (target.tagName === 'A' && target.getAttribute('href') === '#') return;
      target.classList.add('bx-ripple-host');
      var rect = target.getBoundingClientRect();
      var size = Math.max(rect.width, rect.height);
      var span = document.createElement('span');
      span.className = 'bx-ripple';
      span.style.width = span.style.height = size + 'px';
      span.style.left = (e.clientX - rect.left - size / 2) + 'px';
      span.style.top = (e.clientY - rect.top - size / 2) + 'px';
      target.appendChild(span);
      setTimeout(function () { span.remove(); }, 620);
    });
  }

  /* ------------------------------------------------------------------ *
   * 5. BACK TO TOP — nút về đầu trang
   * ------------------------------------------------------------------ */
  function initBackToTop() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bx-to-top';
    btn.setAttribute('aria-label', 'Về đầu trang');
    btn.innerHTML = '<i class="bi bi-arrow-up"></i>';
    document.body.appendChild(btn);
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
    var onScroll = function () {
      if (window.scrollY > 380) btn.classList.add('bx-show');
      else btn.classList.remove('bx-show');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ------------------------------------------------------------------ *
   * 6. PHẢN HỒI CLICK KHÁC — pop badge giỏ hàng khi thay đổi số
   * ------------------------------------------------------------------ */
  function initBadgePop() {
    var badge = document.getElementById('cartBadge');
    if (!badge || reduceMotion) return;
    var last = badge.textContent;
    var observer = new MutationObserver(function () {
      if (badge.textContent !== last) {
        last = badge.textContent;
        badge.classList.remove('bx-pop-anim');
        void badge.offsetWidth;
        badge.classList.add('bx-pop-anim');
      }
    });
    observer.observe(badge, { childList: true, characterData: true, subtree: true });
  }

  /* ------------------------------------------------------------------ *
   * 7. THEO DÕI DOM ĐỘNG — áp lại hiệu ứng cho nội dung AJAX tạo ra
   * ------------------------------------------------------------------ */
  function initMutationHook() {
    if (!('MutationObserver' in window)) return;
    var scheduled = false;
    var observer = new MutationObserver(function (mutations) {
      var relevant = false;
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
          if (node.nodeType === 1 && node.matches && node.matches(ZOOM_SELECTOR + ',' + REVEAL_SELECTOR)) {
            relevant = true;
          }
          if (node.nodeType === 1 && node.querySelectorAll &&
              node.querySelectorAll(ZOOM_SELECTOR + ',' + REVEAL_SELECTOR).length) {
            relevant = true;
          }
        });
      });
      if (relevant && !scheduled) {
        scheduled = true;
        requestAnimationFrame(function () {
          initMedia();
          tagReveals(document);
          scheduled = false;
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* ------------------------------------------------------------------ *
   * KHỞI TẠO
   * ------------------------------------------------------------------ */
  onReady(function () {
    initReveal();
    initMedia();
    buildLightbox();
    initRipple();
    initBackToTop();
    initBadgePop();
    initMutationHook();
  });
})();
