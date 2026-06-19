(function() {
  var c = document.getElementById('constellation');
  if (!c) return;
  var ctx = c.getContext('2d');
  var dots = [];
  var DOT_COUNT = 50;
  var CONNECT_DIST = 160;

  function getThemeParams() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
      dotAlpha: isDark ? 0.3 : 0.15,
      lineAlpha: isDark ? 0.08 : 0.04
    };
  }

  function getAccentRGB() {
    var accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
    if (accent.startsWith('#')) {
      var hex = accent.slice(1);
      return [parseInt(hex.slice(0,2),16), parseInt(hex.slice(2,4),16), parseInt(hex.slice(4,6),16)].join(',');
    }
    return '50,108,229';
  }

  function resize() {
    c.width = window.innerWidth;
    c.height = window.innerHeight;
  }

  function initDots() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    dots = [];
    for (var i = 0; i < DOT_COUNT; i++) {
      dots.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r: Math.random() * 1.5 + 0.5
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, c.width, c.height);
    var p = getThemeParams();
    var col = getAccentRGB();

    for (var i = 0; i < dots.length; i++) {
      var d = dots[i];
      d.x += d.vx;
      d.y += d.vy;
      if (d.x < 0 || d.x > c.width) d.vx *= -1;
      if (d.y < 0 || d.y > c.height) d.vy *= -1;

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + col + ',' + p.dotAlpha + ')';
      ctx.fill();

      for (var j = i + 1; j < dots.length; j++) {
        var dx = dots[j].x - d.x, dy = dots[j].y - d.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONNECT_DIST) {
          ctx.beginPath();
          ctx.moveTo(d.x, d.y);
          ctx.lineTo(dots[j].x, dots[j].y);
          ctx.strokeStyle = 'rgba(' + col + ',' + (p.lineAlpha * (1 - dist / CONNECT_DIST)) + ')';
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', function() {
    resize();
  });

  resize();
  initDots();
  requestAnimationFrame(draw);
})();
