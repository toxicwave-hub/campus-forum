/* CYBER FORUM — Frontend interactions */
(function () {
  'use strict';

  function getCookie(name) {
    var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match.pop()) : '';
  }

  function postJSON(url, body) {
    var fd;
    if (body instanceof FormData) fd = body;
    else {
      fd = new FormData();
      Object.keys(body || {}).forEach(function (k) { fd.append(k, body[k]); });
    }
    return fetch(url, {
      method: 'POST',
      body: fd,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      credentials: 'same-origin',
    });
  }

  // ---------------- Particle FX ----------------
  var canvas = document.createElement('canvas');
  canvas.className = 'fx-canvas';
  document.body.appendChild(canvas);
  var ctx = canvas.getContext('2d');
  var particles = [];
  var dpr = window.devicePixelRatio || 1;

  function resizeCanvas() {
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  var palette = ['#00f0ff', '#ff00d4', '#b300ff', '#fff200', '#00ff9d'];

  function spawnBurst(x, y, opts) {
    opts = opts || {};
    var count = opts.count || 28;
    var minSpeed = opts.minSpeed || 2.4;
    var maxSpeed = opts.maxSpeed || 7;
    var colors = opts.colors || palette;
    for (var i = 0; i < count; i++) {
      var ang = Math.random() * Math.PI * 2;
      var spd = minSpeed + Math.random() * (maxSpeed - minSpeed);
      particles.push({
        x: x, y: y,
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd,
        life: 0,
        max: 40 + Math.random() * 30,
        size: 2 + Math.random() * 3,
        color: colors[Math.floor(Math.random() * colors.length)],
      });
    }
  }

  function spawnHearts(x, y) {
    for (var i = 0; i < 14; i++) {
      var ang = -Math.PI / 2 + (Math.random() - 0.5) * 1.4;
      var spd = 2 + Math.random() * 3;
      particles.push({
        x: x, y: y,
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd,
        life: 0, max: 50 + Math.random() * 30,
        size: 12 + Math.random() * 6,
        color: '#ff00d4',
        glyph: '❤',
      });
    }
  }

  function spawnStars(x, y) {
    for (var i = 0; i < 18; i++) {
      var ang = Math.random() * Math.PI * 2;
      var spd = 2 + Math.random() * 4;
      particles.push({
        x: x, y: y,
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd,
        life: 0, max: 50 + Math.random() * 20,
        size: 14 + Math.random() * 6,
        color: '#fff200',
        glyph: '★',
      });
    }
  }

  function tick() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (var i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      p.life++;
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.12; // gravity
      p.vx *= 0.985;
      var t = p.life / p.max;
      if (t >= 1) { particles.splice(i, 1); continue; }
      var alpha = 1 - t;
      ctx.globalAlpha = alpha;
      if (p.glyph) {
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 14 * alpha;
        ctx.font = p.size + 'px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(p.glyph, p.x, p.y);
      } else {
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 12 * alpha;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    }
    requestAnimationFrame(tick);
  }
  tick();

  function elCenter(el) {
    var r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }

  // ---------------- Spotlight on cards ----------------
  document.querySelectorAll('.card, .board-card').forEach(function (card) {
    card.addEventListener('mousemove', function (event) {
      var rect = card.getBoundingClientRect();
      var mx = ((event.clientX - rect.left) / rect.width) * 100;
      var my = ((event.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty('--mx', mx + '%');
      card.style.setProperty('--my', my + '%');
    });
    card.addEventListener('mouseleave', function () {
      card.style.removeProperty('--mx');
      card.style.removeProperty('--my');
    });
  });

  // ---------------- Auto-dismiss flash ----------------
  document.querySelectorAll('.flash').forEach(function (el) {
    setTimeout(function () { el.remove(); }, 4800);
  });

  // ---------------- Ripple click on buttons ----------------
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.button, .action-btn, .vote-btn');
    if (!btn) return;
    var rect = btn.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height);
    var ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    var cs = getComputedStyle(btn);
    if (cs.position === 'static') btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(function () { ripple.remove(); }, 700);
  });

  // ---------------- AJAX voting ----------------
  document.querySelectorAll('form[data-vote-form]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      var clicked = event.submitter;
      if (!clicked) return;
      event.preventDefault();
      var fd = new FormData(form);
      fd.set('value', clicked.value);
      postJSON(form.action, fd)
        .then(function (r) { if (r.redirected) { window.location = r.url; return null; } return r.json(); })
        .then(function (data) {
          if (!data) return;
          updateVoteUI(form, data, clicked);
        })
        .catch(function () { form.submit(); });
    });
  });

  function updateVoteUI(form, data, clicked) {
    var up = form.querySelector('.vote-up');
    var down = form.querySelector('.vote-down');
    var score = form.querySelector('.vote-score');
    if (score && typeof data.score !== 'undefined') {
      score.textContent = data.score;
      score.classList.remove('pop');
      void score.offsetWidth;
      score.classList.add('pop');
    }
    if (up && down) {
      up.classList.toggle('is-active', data.value === 1);
      down.classList.toggle('is-active', data.value === -1);
      up.value = data.value === 1 ? 0 : 1;
      down.value = data.value === -1 ? 0 : -1;
    }
    // FX: upvote -> stars, downvote -> small purple burst
    if (clicked) {
      var c = elCenter(clicked);
      if (data.value === 1) spawnStars(c.x, c.y);
      else if (data.value === -1) spawnBurst(c.x, c.y, { colors: ['#b300ff', '#7c3aed'], count: 16 });
      else spawnBurst(c.x, c.y, { count: 12 });
    }
  }


  // ---------------- AJAX bookmark ----------------
  document.querySelectorAll('form[data-bookmark-form]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var btn = form.querySelector('button');
      postJSON(form.action)
        .then(function (r) { if (r.redirected) { window.location = r.url; return null; } return r.json(); })
        .then(function (data) {
          if (!data) return;
          var on = !!data.bookmarked;
          btn.classList.toggle('is-active', on);
          var heart = btn.querySelector('.heart');
          if (heart) heart.textContent = on ? '★' : '☆';
          var label = btn.querySelector('.label');
          if (label) label.textContent = on ? '已收藏' : '收藏';
          var c = elCenter(btn);
          if (on) spawnStars(c.x, c.y);
        })
        .catch(function () { form.submit(); });
    });
  });

  // ---------------- AJAX follow ----------------
  document.querySelectorAll('form[data-follow-form]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var btn = form.querySelector('button');
      postJSON(form.action)
        .then(function (r) { if (r.redirected) { window.location = r.url; return null; } return r.json(); })
        .then(function (data) {
          if (!data) return;
          var on = !!data.is_following;
          btn.dataset.following = on ? 'true' : 'false';
          var label = btn.querySelector('.label');
          if (label) label.textContent = on ? '已关注' : '关注';
          var counter = document.querySelector('[data-follower-count]');
          if (counter && typeof data.follower_count === 'number') {
            counter.textContent = data.follower_count;
          }
          var c = elCenter(btn);
          if (on) spawnHearts(c.x, c.y);
          else spawnBurst(c.x, c.y, { colors: ['#9aa9d6'], count: 10 });
        })
        .catch(function () { form.submit(); });
    });
  });

  // ---------------- AJAX subscribe ----------------
  document.querySelectorAll('form[data-subscribe-form]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var btn = form.querySelector('button');
      postJSON(form.action)
        .then(function (r) { if (r.redirected) { window.location = r.url; return null; } return r.json(); })
        .then(function (data) {
          if (!data) return;
          var on = !!data.subscribed;
          btn.dataset.subscribed = on ? 'true' : 'false';
          var label = btn.querySelector('.label');
          if (label) label.textContent = on ? '已订阅' : '订阅';
          var counter = document.querySelector('[data-subscriber-count]');
          if (counter && typeof data.subscriber_count === 'number') {
            counter.textContent = data.subscriber_count;
          }
          var c = elCenter(btn);
          if (on) spawnBurst(c.x, c.y, { colors: ['#00ff9d', '#00f0ff'], count: 24 });
        })
        .catch(function () { form.submit(); });
    });
  });

  // ---------------- Reply target ----------------
  document.querySelectorAll('[data-reply-target]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      event.preventDefault();
      var parentId = link.getAttribute('data-reply-target');
      var name = link.getAttribute('data-reply-name') || '';
      var input = document.getElementById('reply-parent-input');
      var area = document.getElementById('reply-textarea');
      var hint = document.getElementById('reply-target-hint');
      var clearBtn = document.getElementById('reply-target-clear');
      if (input) input.value = parentId;
      if (hint) { hint.textContent = '回复 @' + name; hint.style.display = 'inline-flex'; }
      if (clearBtn) clearBtn.style.display = 'inline-flex';
      if (area) {
        area.focus();
        var top = area.getBoundingClientRect().top + window.pageYOffset - 100;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });
  var clearBtn = document.getElementById('reply-target-clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      var input = document.getElementById('reply-parent-input');
      var hint = document.getElementById('reply-target-hint');
      if (input) input.value = '';
      if (hint) hint.style.display = 'none';
      clearBtn.style.display = 'none';
    });
  }

  // ---------------- @ mention autocomplete ----------------
  document.querySelectorAll('textarea[data-mention-area]').forEach(function (ta) {
    var dropdown = document.createElement('div');
    dropdown.className = 'mention-dropdown';
    document.body.appendChild(dropdown);
    var current = { active: 0, results: [], anchor: -1, query: '' };
    var debounce = null;

    function close() {
      dropdown.classList.remove('is-open');
      current.results = [];
      current.anchor = -1;
    }

    function position() {
      var rect = ta.getBoundingClientRect();
      dropdown.style.top = (rect.top + window.scrollY + 28) + 'px';
      dropdown.style.left = (rect.left + window.scrollX + 16) + 'px';
    }

    function render() {
      if (!current.results.length) { close(); return; }
      dropdown.innerHTML = current.results.map(function (u, i) {
        return '<div class="mention-item' + (i === current.active ? ' is-active' : '') +
          '" data-username="' + u.username + '">' +
          '<span class="avatar" style="width:24px;height:24px;font-size:11px;background:' + u.color + '">' +
          u.initial + '</span>' +
          '<span>@' + u.username + '</span>' +
          (u.nickname && u.nickname !== u.username ? '<span class="nickname">' + u.nickname + '</span>' : '') +
        '</div>';
      }).join('');
      Array.from(dropdown.querySelectorAll('.mention-item')).forEach(function (it, i) {
        it.addEventListener('mousedown', function (e) {
          e.preventDefault();
          current.active = i;
          select();
        });
      });
      position();
      dropdown.classList.add('is-open');
    }

    function select() {
      var u = current.results[current.active];
      if (!u || current.anchor < 0) return;
      var before = ta.value.slice(0, current.anchor);
      var after = ta.value.slice(ta.selectionStart);
      var insert = '@' + u.username + ' ';
      ta.value = before + insert + after;
      var pos = before.length + insert.length;
      ta.setSelectionRange(pos, pos);
      ta.focus();
      close();
    }

    function detect() {
      var pos = ta.selectionStart;
      var text = ta.value.slice(0, pos);
      var m = text.match(/(?:^|\s)@([A-Za-z0-9_\u4e00-\u9fa5]{0,20})$/);
      if (!m) { close(); return; }
      current.anchor = pos - m[1].length - 1;
      current.query = m[1];
      if (debounce) clearTimeout(debounce);
      debounce = setTimeout(function () {
        if (current.query.length === 0) { close(); return; }
        fetch('/api/users/search/?q=' + encodeURIComponent(current.query), { credentials: 'same-origin' })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (data) {
            if (!data || !data.results) { close(); return; }
            current.results = data.results;
            current.active = 0;
            render();
          });
      }, 120);
    }

    ta.addEventListener('input', detect);
    ta.addEventListener('keydown', function (e) {
      if (!dropdown.classList.contains('is-open')) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); current.active = (current.active + 1) % current.results.length; render(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); current.active = (current.active - 1 + current.results.length) % current.results.length; render(); }
      else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); select(); }
      else if (e.key === 'Escape') { close(); }
    });
    ta.addEventListener('blur', function () { setTimeout(close, 120); });
  });

  // ---------------- Chat auto-scroll ----------------
  var chatBody = document.getElementById('chat-body');
  if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;

  // ---------------- File upload preview ----------------
  document.querySelectorAll('input[type="file"][name="attachments"]').forEach(function (input) {
    input.addEventListener('change', function () {
      var label = input.closest('.upload-label');
      if (!label) return;
      var n = input.files.length;
      Array.from(label.childNodes).forEach(function (node) {
        if (node.nodeType === 3) label.removeChild(node);
      });
      var text = document.createTextNode(n ? '📎 已选择 ' + n + ' 个文件' : '📎 添加图片 / 视频 / 文件');
      label.insertBefore(text, label.firstChild);
    });
  });

  // ---------------- Navbar scroll shadow ----------------
  var nav = document.querySelector('.navbar');
  if (nav) {
    var onScroll = function () {
      if (window.scrollY > 8) nav.style.boxShadow = '0 1px 0 var(--border), 0 0 30px rgba(0, 240, 255, 0.12)';
      else nav.style.boxShadow = '';
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
})();


/* ---------------- Floating buttons + Command palette + Cursor trail ---------------- */
(function () {
  // FAB stack
  var fabStack = document.createElement('div');
  fabStack.className = 'fab-stack';
  fabStack.innerHTML =
    '<button class="fab" id="fab-cmdk" aria-label="命令面板"><span class="fab-label">⌘K 命令</span>⌘</button>' +
    '<button class="fab" id="fab-top" aria-label="回到顶部" style="display:none"><span class="fab-label">回到顶部</span>↑</button>';
  document.body.appendChild(fabStack);

  var fabTop = document.getElementById('fab-top');
  window.addEventListener('scroll', function () {
    fabTop.style.display = window.scrollY > 400 ? 'inline-flex' : 'none';
  }, { passive: true });
  fabTop.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Command palette
  var overlay = document.createElement('div');
  overlay.className = 'cmdk-overlay';
  overlay.innerHTML =
    '<div class="cmdk-panel">' +
      '<input class="cmdk-input" type="text" placeholder="// 输入指令、搜索帖子或跳转用户..." autofocus>' +
      '<div class="cmdk-list"></div>' +
    '</div>';
  document.body.appendChild(overlay);
  var input = overlay.querySelector('.cmdk-input');
  var list = overlay.querySelector('.cmdk-list');
  var nav = [
    { icon: '🏠', label: '首页', href: '/', kbd: 'g h' },
    { icon: '🔥', label: '热门', href: '/?sort=hot', kbd: 'g f' },
    { icon: '🆕', label: '最新', href: '/?sort=new', kbd: 'g n' },
    { icon: '☕', label: '闲聊板块', href: '/boards/chemical-study/' },
    { icon: '🤖', label: 'AI 工具板块', href: '/boards/ai-tools/' },
    { icon: '🚀', label: '项目交流板块', href: '/boards/project-exchange/' },
    { icon: '✉', label: '私信', href: '/messages/' },
    { icon: '🔔', label: '通知', href: '/notifications/' },
    { icon: '★', label: '收藏', href: '/me/bookmarks/' },
    { icon: '✎', label: '草稿', href: '/me/drafts/' },
    { icon: '⚙', label: '编辑主页', href: '/me/profile/edit/' },
    { icon: '🚪', label: '退出', href: '/accounts/logout/' },
  ];
  var current = { items: nav, active: 0 };

  function render() {
    list.innerHTML = current.items.map(function (it, i) {
      return '<a class="cmdk-item' + (i === current.active ? ' is-active' : '') + '" href="' + it.href + '">' +
        '<span class="cmdk-icon">' + it.icon + '</span>' +
        '<span>' + it.label + '</span>' +
        (it.kbd ? '<span class="kbd">' + it.kbd + '</span>' : '') +
        '</a>';
    }).join('');
  }

  function open() {
    overlay.classList.add('is-open');
    input.value = '';
    current.items = nav;
    current.active = 0;
    render();
    setTimeout(function () { input.focus(); }, 50);
  }
  function close() {
    overlay.classList.remove('is-open');
  }

  document.getElementById('fab-cmdk').addEventListener('click', open);
  overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault(); open();
    }
    if (overlay.classList.contains('is-open')) {
      if (e.key === 'Escape') { close(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); current.active = Math.min(current.items.length - 1, current.active + 1); render(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); current.active = Math.max(0, current.active - 1); render(); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var it = current.items[current.active];
        if (it) {
          if (it.searchHref) { window.location = it.searchHref; }
          else { window.location = it.href; }
        }
      }
    }
  });

  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    if (!q) { current.items = nav; current.active = 0; render(); return; }
    var filtered = nav.filter(function (it) {
      return it.label.toLowerCase().indexOf(q) !== -1;
    });
    filtered.unshift({
      icon: '🔍', label: '搜索 "' + input.value + '"',
      href: '/search/?q=' + encodeURIComponent(input.value),
    });
    current.items = filtered;
    current.active = 0;
    render();
  });

  // Cursor trail (skip on touch devices)
  if (!('ontouchstart' in window)) {
    var trail = document.createElement('div');
    trail.className = 'cursor-trail';
    document.body.appendChild(trail);
    var x = 0, y = 0, tx = 0, ty = 0;
    document.addEventListener('mousemove', function (e) { x = e.clientX; y = e.clientY; });
    function loop() {
      tx += (x - tx) * 0.18;
      ty += (y - ty) * 0.18;
      trail.style.transform = 'translate(' + tx + 'px,' + ty + 'px)';
      requestAnimationFrame(loop);
    }
    loop();
  }
})();
