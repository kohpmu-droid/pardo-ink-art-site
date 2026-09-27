// כפתור שיתוף צף בכל דף.
// למה: בדפדפנים שנפתחים מתוך אינסטגרם/פייסבוק/וואטסאפ אין שורת כתובת,
// ולכן אין דרך להעתיק קישור לדף. בטלפון נפתח תפריט השיתוף של המכשיר;
// איפה שאין כזה (מחשב, חלק מהדפדפנים הפנימיים) נפתח חלון קטן עם וואטסאפ,
// פייסבוק והעתקת קישור.
(function () {
  var canonical = document.querySelector('link[rel="canonical"]');
  var url = canonical ? canonical.href : location.origin + location.pathname;
  var title = document.title;

  var css = ''
    + '#share-btn{position:fixed;bottom:18px;inset-inline-end:18px;z-index:9999;width:56px;height:56px;border-radius:50%;'
    + 'background:#5e2b3a;color:#f7efe9;border:2px solid #f7efe9;box-shadow:0 6px 20px rgba(0,0,0,.25);cursor:pointer;'
    + 'display:flex;align-items:center;justify-content:center;padding:0;}'
    + '#share-btn:hover{background:#4a2230;}'
    + '#share-btn svg{width:24px;height:24px;}'
    + '#share-panel{position:fixed;bottom:84px;inset-inline-end:18px;z-index:9999;width:240px;max-width:calc(100vw - 36px);'
    + 'background:#fff;color:#3d2a2e;border:1px solid #b79891;border-radius:14px;box-shadow:0 14px 40px rgba(0,0,0,.28);'
    + 'padding:14px;font-family:Assistant,sans-serif;display:none;}'
    + '#share-panel.open{display:grid;gap:8px;}'
    + '#share-panel h3{font-family:"Frank Ruhl Libre",serif;color:#5e2b3a;font-size:1.1rem;margin:0 0 4px;text-align:center;}'
    + '#share-panel a,#share-panel button{display:block;background:#f7f2ea;border:1px solid #d9c7bf;border-radius:9px;padding:10px 8px;'
    + 'cursor:pointer;font-size:.95rem;color:#3d2a2e;font-family:inherit;text-align:center;text-decoration:none;}'
    + '#share-panel a:hover,#share-panel button:hover{border-color:#5e2b3a;}';
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var btn = document.createElement('button');
  btn.id = 'share-btn';
  btn.type = 'button';
  btn.setAttribute('aria-label', 'שיתוף הדף');
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-controls', 'share-panel');
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
    + '<line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/></svg>';

  var panel = document.createElement('div');
  panel.id = 'share-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'שיתוף הדף');
  var enc = encodeURIComponent;
  panel.innerHTML = '<h3>שיתוף הדף</h3>'
    + '<a href="https://wa.me/?text=' + enc(title + '\n' + url) + '" target="_blank" rel="noopener">וואטסאפ</a>'
    + '<a href="https://www.facebook.com/sharer/sharer.php?u=' + enc(url) + '" target="_blank" rel="noopener">פייסבוק</a>'
    + '<button type="button" id="share-copy">העתקת קישור</button>';

  document.body.appendChild(panel);
  document.body.appendChild(btn);

  function setOpen(open) {
    panel.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open);
  }

  btn.addEventListener('click', function () {
    if (navigator.share) {
      navigator.share({ title: title, url: url }).catch(function () {});
      return;
    }
    setOpen(!panel.classList.contains('open'));
  });

  document.addEventListener('click', function (e) {
    if (!panel.contains(e.target) && !btn.contains(e.target)) setOpen(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') setOpen(false);
  });

  var copyBtn = panel.querySelector('#share-copy');
  function copied() {
    copyBtn.textContent = 'הקישור הועתק ✓';
    setTimeout(function () { copyBtn.textContent = 'העתקת קישור'; }, 2000);
  }
  function legacyCopy() {
    var ta = document.createElement('textarea');
    ta.value = url;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
    if (ok) copied(); else window.prompt('הקישור לדף:', url);
  }
  copyBtn.addEventListener('click', function () {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(url).then(copied, legacyCopy);
    } else {
      legacyCopy();
    }
  });
})();
