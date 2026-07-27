(function () {
  var root = document.documentElement;
  var KEY = 'pardo_a11y_v1';
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { state = {}; }
  if (typeof state.font !== 'number') state.font = 1;

  var css = ''
    + '#a11y-btn{position:fixed;bottom:18px;inset-inline-start:18px;z-index:9999;width:56px;height:56px;border-radius:50%;'
    + 'background:#5e2b3a;color:#f7efe9;border:2px solid #f7efe9;box-shadow:0 6px 20px rgba(0,0,0,.25);cursor:pointer;'
    + 'display:flex;align-items:center;justify-content:center;font-size:28px;line-height:1;}'
    + '#a11y-btn:hover{background:#4a2230;}'
    + '#a11y-panel{position:fixed;bottom:84px;inset-inline-start:18px;z-index:9999;width:280px;max-width:calc(100vw - 36px);'
    + 'background:#fff;color:#3d2a2e;border:1px solid #b79891;border-radius:14px;box-shadow:0 14px 40px rgba(0,0,0,.28);'
    + 'padding:16px;font-family:Assistant,sans-serif;display:none;}'
    + '#a11y-panel.open{display:block;}'
    + '#a11y-panel h3{font-family:"Frank Ruhl Libre",serif;color:#5e2b3a;font-size:1.15rem;margin:0 0 10px;text-align:center;}'
    + '#a11y-panel .a11y-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}'
    + '#a11y-panel button.opt{background:#f7f2ea;border:1px solid #d9c7bf;border-radius:9px;padding:10px 8px;cursor:pointer;'
    + 'font-size:.9rem;color:#3d2a2e;font-family:inherit;text-align:center;}'
    + '#a11y-panel button.opt:hover{border-color:#5e2b3a;}'
    + '#a11y-panel button.opt.active{background:#5e2b3a;color:#f7efe9;border-color:#5e2b3a;}'
    + '#a11y-panel .a11y-reset{grid-column:1 / -1;background:#efe6d8;}'
    + '#a11y-panel .a11y-stmt{display:block;text-align:center;margin-top:12px;color:#5e2b3a;text-decoration:underline;font-size:.85rem;}'
    // effect classes
    + 'html.a11y-readable, html.a11y-readable *{font-family:Arial,"Assistant",sans-serif !important;letter-spacing:.01em !important;}'
    + 'html.a11y-links a{text-decoration:underline !important;background:#fff2b8 !important;color:#3d2a2e !important;box-shadow:0 0 0 2px #fff2b8;}'
    + 'html.a11y-gray, html.a11y-gray body{filter:grayscale(1) !important;}'
    + 'html.a11y-contrast, html.a11y-contrast body{background:#000 !important;color:#fff !important;}'
    + 'html.a11y-contrast .card,html.a11y-contrast .bg-cream-alt,html.a11y-contrast section,html.a11y-contrast nav,html.a11y-contrast footer{background:#000 !important;}'
    + 'html.a11y-contrast h1,html.a11y-contrast h2,html.a11y-contrast h3,html.a11y-contrast p,html.a11y-contrast span,html.a11y-contrast li,html.a11y-contrast a{color:#fff !important;}'
    + 'html.a11y-contrast a{color:#ffd400 !important;}'
    + 'html.a11y-contrast .btn-wine,html.a11y-contrast .bg-wine{background:#ffd400 !important;color:#000 !important;}';

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  function apply() {
    root.style.fontSize = Math.round(state.font * 100) + '%';
    root.classList.toggle('a11y-readable', !!state.readable);
    root.classList.toggle('a11y-links', !!state.links);
    root.classList.toggle('a11y-gray', !!state.gray);
    root.classList.toggle('a11y-contrast', !!state.contrast);
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    ['readable', 'links', 'gray', 'contrast'].forEach(function (k) {
      var b = document.getElementById('a11y-' + k);
      if (b) b.classList.toggle('active', !!state[k]);
    });
  }

  function build() {
    var btn = document.createElement('button');
    btn.id = 'a11y-btn';
    btn.setAttribute('aria-label', 'תפריט נגישות');
    btn.setAttribute('aria-haspopup', 'true');
    btn.innerHTML = '<span aria-hidden="true">&#9855;</span>';

    var panel = document.createElement('div');
    panel.id = 'a11y-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'הגדרות נגישות');
    panel.innerHTML =
      '<h3>תפריט נגישות</h3>' +
      '<div class="a11y-grid">' +
      '<button class="opt" id="a11y-font-plus">א+ הגדלת טקסט</button>' +
      '<button class="opt" id="a11y-font-minus">א- הקטנת טקסט</button>' +
      '<button class="opt" id="a11y-contrast">ניגודיות גבוהה</button>' +
      '<button class="opt" id="a11y-gray">גווני אפור</button>' +
      '<button class="opt" id="a11y-links">הדגשת קישורים</button>' +
      '<button class="opt" id="a11y-readable">גופן קריא</button>' +
      '<button class="opt a11y-reset" id="a11y-reset">איפוס הגדרות</button>' +
      '</div>' +
      '<a class="a11y-stmt" href="accessibility.html">להצהרת הנגישות</a>';

    document.body.appendChild(btn);
    document.body.appendChild(panel);

    btn.addEventListener('click', function () { panel.classList.toggle('open'); });
    document.addEventListener('click', function (e) {
      if (!panel.contains(e.target) && e.target !== btn && !btn.contains(e.target)) panel.classList.remove('open');
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') panel.classList.remove('open'); });

    document.getElementById('a11y-font-plus').addEventListener('click', function () { state.font = Math.min(1.6, state.font + 0.1); apply(); });
    document.getElementById('a11y-font-minus').addEventListener('click', function () { state.font = Math.max(0.9, state.font - 0.1); apply(); });
    document.getElementById('a11y-contrast').addEventListener('click', function () { state.contrast = !state.contrast; apply(); });
    document.getElementById('a11y-gray').addEventListener('click', function () { state.gray = !state.gray; apply(); });
    document.getElementById('a11y-links').addEventListener('click', function () { state.links = !state.links; apply(); });
    document.getElementById('a11y-readable').addEventListener('click', function () { state.readable = !state.readable; apply(); });
    document.getElementById('a11y-reset').addEventListener('click', function () { state = { font: 1 }; apply(); });

    apply();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
