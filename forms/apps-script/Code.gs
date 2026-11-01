/**
 * קולט את טפסי הצהרת הבריאות מהאתר (forms/*.html) ושומר אותם בדרייב של כוכבית.
 *
 * לכל לקוח/ה תיקייה משלו/ה בתוך תיקיית השירות: "שם מלא – 0501234567".
 * לקוח/ה שחוזר/ת (אותו טלפון) נכנס/ת לאותה תיקייה. בכל שליחה נשמרים:
 *   - PDF של ההצהרה עם החתימה
 *   - צילומי אריזות תרופות, אם צורפו
 *   - שורה ביומן "יומן הצהרות בריאות" בתיקיית השירות
 * ונשלח מייל לבעלת החשבון. אם סומן סעיף שמחייב אישור רופא, זה כתוב בכותרת.
 *
 * פריסה: script.google.com ← פרויקט חדש ← להדביק את הקובץ ← Deploy ← New deployment
 * ← Web app ← Execute as: Me ← Who has access: Anyone. הכתובת שמתקבלת נכנסת
 * ל-forms/config.js באתר.
 */

// תיקיית השירות בדרייב לכל טופס. שירות חדש = שורה חדשה כאן.
const ROOT_FOLDERS = {
  laser: '1ySBpWBcMflPKTAKL97l_dwILSHKw-IBf', // אתר / לקוחות הסרה בלייזר
};

const LOG_NAME = 'יומן הצהרות בריאות';
const TZ = 'Asia/Jerusalem';
const MAX_PER_PHONE = 3; // שליחות מאותו טלפון בתוך 10 דקות

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.website) return json_({ ok: true }); // מלכודת לבוטים
    const rootId = ROOT_FOLDERS[d.service];
    if (!rootId) throw new Error('unknown service');
    const c = d.client || {};
    const phone = normPhone_(c.phone);
    if (!c.name || !phone || !d.signature) throw new Error('missing fields');
    if (!rateOk_(phone)) throw new Error('too many submissions');

    const lock = LockService.getScriptLock();
    lock.waitLock(20000);
    let folder;
    try {
      folder = clientFolder_(DriveApp.getFolderById(rootId), c.name, phone);
    } finally {
      lock.releaseLock();
    }

    const now = new Date();
    const stamp = Utilities.formatDate(now, TZ, 'yyyy-MM-dd HH-mm');
    const html = buildHtml_(d, Utilities.formatDate(now, TZ, 'dd/MM/yyyy HH:mm'));
    const pdf = Utilities.newBlob(html, 'text/html', 'form.html')
      .getAs('application/pdf')
      .setName('הצהרת בריאות ' + d.serviceTitle + ' ' + stamp + '.pdf');
    const file = folder.createFile(pdf);

    (d.photos || []).slice(0, 3).forEach(function (p, i) {
      const m = String(p).match(/^data:(image\/\w+);base64,(.+)$/);
      if (m) folder.createFile(Utilities.newBlob(Utilities.base64Decode(m[2]), m[1], 'תרופות ' + stamp + ' ' + (i + 1) + '.jpg'));
    });

    log_(DriveApp.getFolderById(rootId), d, phone, folder, file, now);
    notify_(d, folder, file);
    return json_({ ok: true });
  } catch (err) {
    console.error(err);
    return json_({ ok: false, error: String(err && err.message || err) });
  }
}

function doGet() {
  return json_({ ok: true, service: 'pardo-forms' });
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

/** 050-123-4567 / +972501234567 ← 0501234567 */
function normPhone_(p) {
  let d = String(p || '').replace(/\D/g, '');
  if (d.indexOf('972') === 0) d = '0' + d.slice(3);
  return /^0\d{8,9}$/.test(d) ? d : '';
}

function rateOk_(phone) {
  const cache = CacheService.getScriptCache();
  const k = 'n_' + phone;
  const n = Number(cache.get(k) || 0);
  if (n >= MAX_PER_PHONE) return false;
  cache.put(k, String(n + 1), 600);
  return true;
}

/** התיקייה של הלקוח/ה לפי טלפון. נוצרת בשליחה הראשונה. */
function clientFolder_(root, name, phone) {
  const it = root.getFolders();
  while (it.hasNext()) {
    const f = it.next();
    if (f.getName().replace(/\D/g, '').indexOf(phone) !== -1) return f;
  }
  return root.createFolder(String(name).trim() + ' – ' + phone);
}

function esc_(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, function (ch) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch];
  });
}

const POLICY_LABEL = { doc: 'אישור רופא', stop: 'לא מטפלים', wait: 'דחייה', note: 'שיחה' };

function buildHtml_(d, when) {
  const c = d.client || {};
  const f = d.flags || {};
  let h = '<html dir="rtl"><head><meta charset="utf-8"><style>' +
    'body{font-family:Arial,sans-serif;direction:rtl;color:#2b1d20;font-size:11pt}' +
    'h1{font-size:17pt;color:#5e2b3a;margin:0 0 4px}h2{font-size:12.5pt;color:#5e2b3a;margin:16px 0 6px;border-bottom:1px solid #5e2b3a}' +
    'table{width:100%;border-collapse:collapse}td{border-bottom:1px solid #ddd;padding:4px 6px;vertical-align:top;text-align:right}' +
    'td.a{width:32%;font-weight:bold}.tag{font-weight:bold;color:#5e2b3a}.box{border:2px solid #5e2b3a;padding:8px 10px;margin:10px 0}' +
    '.muted{color:#777;font-size:9pt}</style></head><body>';
  h += '<div class="muted">Pardo Ink Art · כוכבית פרדו · כרמי גת סנטר, קומה 1 · 055-284-5920</div>';
  h += '<h1>הצהרת בריאות — ' + esc_(d.serviceTitle) + '</h1>';
  h += '<div class="muted">נשלח מהאתר: ' + esc_(when) + ' · גרסת טופס ' + esc_(d.version) + '</div>';

  if ((f.stop || []).length || (f.doc || []).length || (f.wait || []).length) {
    h += '<div class="box">';
    if ((f.stop || []).length) h += '<div><span class="tag">לא מטפלים:</span> ' + f.stop.map(esc_).join(' · ') + '</div>';
    if ((f.doc || []).length) h += '<div><span class="tag">נדרש אישור רופא:</span> ' + f.doc.map(esc_).join(' · ') + '</div>';
    if ((f.wait || []).length) h += '<div><span class="tag">ייתכן שנדחה:</span> ' + f.wait.map(esc_).join(' · ') + '</div>';
    h += '</div>';
  }

  (d.sections || []).forEach(function (s) {
    h += '<h2>' + esc_(s.title) + '</h2><table>';
    (s.rows || []).forEach(function (r) {
      const pol = r.policy ? ' <span class="tag">[' + esc_(POLICY_LABEL[r.policy] || r.policy) + ']</span>' : '';
      h += '<tr><td>' + esc_(r.label) + pol + (r.detail ? '<br><span class="muted">' + esc_(r.detail) + '</span>' : '') +
        '</td><td class="a">' + esc_(r.answer) + '</td></tr>';
    });
    h += '</table>';
  });

  if (c.parentName) {
    h += '<h2>הורה או אפוטרופוס</h2><p>' + esc_(c.parentName) + ' · ' + esc_(c.parentPhone) + '</p>';
  }
  h += '<h2>הצהרה</h2><ol>' + (d.declaration || []).map(function (x) { return '<li>' + esc_(x) + '</li>'; }).join('') + '</ol>';
  h += '<p>' + (d.agreements || []).map(function (x) { return '☑ ' + esc_(x); }).join('<br>') + '</p>';
  h += '<p><b>' + esc_(c.name) + '</b> · ת.ז. ' + esc_(c.idNumber) + ' · ' + esc_(when) + '</p>';
  h += '<img src="' + d.signature + '" style="width:260px;border-bottom:1px solid #999">';
  h += '<p class="muted">נחתם דיגיטלית בטופס באתר pardoinkart.com</p>';
  return h + '</body></html>';
}

function log_(root, d, phone, folder, file, now) {
  const it = root.getFilesByName(LOG_NAME);
  let ss;
  if (it.hasNext()) {
    ss = SpreadsheetApp.open(it.next());
  } else {
    ss = SpreadsheetApp.create(LOG_NAME);
    DriveApp.getFileById(ss.getId()).moveTo(root);
    ss.getSheets()[0].appendRow(['תאריך', 'שם', 'טלפון', 'גיל', 'לא מטפלים', 'אישור רופא', 'דחייה', 'תיקייה', 'PDF']);
    ss.getSheets()[0].setFrozenRows(1);
  }
  const f = d.flags || {};
  ss.getSheets()[0].appendRow([
    Utilities.formatDate(now, TZ, 'dd/MM/yyyy HH:mm'), d.client.name, "'" + phone, d.client.age,
    (f.stop || []).join(', '), (f.doc || []).join(', '), (f.wait || []).join(', '),
    folder.getUrl(), file.getUrl()
  ]);
}

function notify_(d, folder, file) {
  const f = d.flags || {};
  const to = Session.getEffectiveUser().getEmail();
  let subject = 'הצהרת בריאות חדשה: ' + d.client.name + ' (' + d.serviceTitle + ')';
  if ((f.stop || []).length) subject = '⛔ לא מטפלים — ' + subject;
  else if ((f.doc || []).length) subject = '⚠️ נדרש אישור רופא — ' + subject;
  let body = '<div dir="rtl" style="font-family:Arial">';
  if ((f.stop || []).length) body += '<p><b>לא מטפלים:</b> ' + f.stop.map(esc_).join(', ') + '</p>';
  if ((f.doc || []).length) body += '<p><b>אישור רופא:</b> ' + f.doc.map(esc_).join(', ') + '</p>';
  if ((f.wait || []).length) body += '<p><b>ייתכן שנדחה:</b> ' + f.wait.map(esc_).join(', ') + '</p>';
  body += '<p><a href="' + file.getUrl() + '">ההצהרה (PDF)</a> · <a href="' + folder.getUrl() + '">תיקיית הלקוח/ה</a></p></div>';
  MailApp.sendEmail({ to: to, subject: subject, htmlBody: body });
}

/** להרצה ידנית מהעורך אחרי הפריסה: יוצר תיקיית בדיקה עם PDF ומייל, כדי לראות שהכל עובד. */
function testSubmit() {
  const sample = {
    service: 'laser', serviceTitle: 'הסרת קעקוע בלייזר', version: 'test',
    client: { name: 'בדיקה בדיקה', phone: '0500000000', idNumber: '000000018', age: 30 },
    sections: [{ title: 'מחלות ומצבי רקע', rows: [{ label: 'סוכרת', answer: 'כן', detail: 'סוג 2, מאוזנת', policy: 'doc' }] }],
    flags: { doc: ['סוכרת'], stop: [], wait: [], note: [] },
    declaration: ['מסרתי מידע מלא ונכון.'], agreements: ['קראתי ואני מאשר/ת את ההצהרה.'],
    signature: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
    photos: []
  };
  const res = doPost({ postData: { contents: JSON.stringify(sample) } });
  console.log(res.getContent());
}
