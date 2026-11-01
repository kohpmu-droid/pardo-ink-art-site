// מנוע טפסי הצהרת הבריאות. כל שירות (laser.html, ובהמשך קעקוע, פירסינג...) מגדיר
// window.PARDO_FORM עם השאלות, והקובץ הזה בונה את הטופס, מסמן מתי נדרש אישור רופא,
// אוסף חתימה ושולח ל-Apps Script ששומר PDF בתיקיית הלקוח בדרייב.
(function () {
  var F = window.PARDO_FORM;
  var root = document.getElementById("form");
  var POL = {
    doc: "נדרש אישור רופא בכתב לפני הטיפול.",
    stop: "במצב הזה לא ניתן לבצע הסרה בלייזר. נדבר על זה אישית.",
    wait: "ייתכן שנצטרך לדחות את הטיפול. נתאם יחד.",
    note: "נעבור על זה יחד לפני הטיפול."
  };

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "class") e.className = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    if (html != null) e.innerHTML = html;
    return e;
  }

  // ---------- בניית הטופס ----------
  F.sections.forEach(function (sec) {
    var card = el("section", { class: "card", id: "sec-" + sec.id });
    card.appendChild(el("h2", null, sec.title));
    if (sec.sub) card.appendChild(el("p", { class: "sub" }, sec.sub));

    if (sec.type === "fields") {
      var g = el("div", { class: "grid2" });
      sec.fields.forEach(function (f) {
        var lab = el("label", { class: "f" + (f.wide ? " wide" : "") });
        lab.appendChild(el("span", { class: f.required ? "req" : "" }, f.label));
        var inp = el(f.type === "textarea" ? "textarea" : "input", {
          id: f.id, name: f.id, type: f.type || "text",
          autocomplete: f.autocomplete || "off"
        });
        if (f.inputmode) inp.setAttribute("inputmode", f.inputmode);
        if (f.placeholder) inp.setAttribute("placeholder", f.placeholder);
        if (f.required) inp.required = true;
        lab.appendChild(inp);
        if (f.hint) lab.appendChild(el("small", null, f.hint));
        if (f.wide) lab.style.gridColumn = "1 / -1";
        g.appendChild(lab);
      });
      card.appendChild(g);
    }

    if (sec.type === "yesno") {
      sec.items.forEach(function (it) {
        var q = el("div", { class: "q", id: "q-" + it.id });
        q.appendChild(el("div", { class: "qt" }, it.q));
        if (it.hint) q.appendChild(el("div", { class: "qh" }, it.hint));
        var yn = el("div", { class: "yn", role: "radiogroup", "aria-label": it.q });
        ["כן", "לא"].forEach(function (v) {
          var l = el("label");
          var r = el("input", { type: "radio", name: it.id, value: v, id: it.id + (v === "כן" ? "-y" : "-n") });
          l.appendChild(r);
          l.appendChild(el("span", null, v));
          yn.appendChild(l);
        });
        q.appendChild(yn);
        var det = el("input", {
          type: "text", class: "detail", id: it.id + "-d", hidden: "",
          placeholder: it.detail || "פירוט"
        });
        q.appendChild(det);
        if (it.policy) {
          q.appendChild(el("div", { class: "pol " + it.policy, id: it.id + "-p", hidden: "" },
            it.policyText || POL[it.policy]));
        }
        card.appendChild(q);
      });
    }

    if (sec.type === "checks") {
      var c = el("div", { class: "checks" });
      sec.options.forEach(function (o) {
        var l = el("label");
        l.appendChild(el("input", { type: "checkbox", name: sec.id, value: o.label, id: sec.id + "-" + o.id, "data-policy": o.policy || "" }));
        l.appendChild(document.createTextNode(o.label));
        c.appendChild(l);
      });
      card.appendChild(c);
      card.appendChild(el("input", { type: "text", id: sec.id + "-d", placeholder: "פירוט, למשל איזו תגובה הייתה" }));
    }

    if (sec.extra) {
      sec.extra.forEach(function (x) {
        if (x.type === "textarea") {
          var lab = el("label", { class: "f" });
          lab.appendChild(el("span", null, x.label));
          lab.appendChild(el("textarea", { id: x.id, placeholder: x.placeholder || "" }));
          card.appendChild(lab);
        }
        if (x.type === "photos") {
          var lab2 = el("label", { class: "f" });
          lab2.appendChild(el("span", null, x.label));
          lab2.appendChild(el("input", { type: "file", id: x.id, accept: "image/*", multiple: "" }));
          lab2.appendChild(el("small", null, "עד 3 תמונות"));
          card.appendChild(lab2);
          card.appendChild(el("div", { class: "photos", id: x.id + "-prev" }));
        }
      });
    }
    root.appendChild(card);
  });

  // ---------- סיכום, הצהרה, חתימה ----------
  var summary = el("section", { class: "summary", id: "summary", hidden: "", "aria-live": "polite" });
  root.appendChild(summary);

  var decl = el("section", { class: "card decl", id: "sec-decl" });
  decl.appendChild(el("h2", null, "הצהרה וחתימה"));
  var ol = el("ol");
  F.declaration.forEach(function (d) { ol.appendChild(el("li", null, d)); });
  decl.appendChild(ol);
  F.agreements.forEach(function (a, i) {
    var l = el("label", { class: "agree", id: "ag-" + i });
    l.appendChild(el("input", { type: "checkbox", id: "agree-" + i }));
    l.appendChild(el("span", null, a));
    decl.appendChild(l);
  });
  var minor = el("div", { class: "grid2", id: "minor", hidden: "" });
  minor.innerHTML =
    '<label class="f"><span class="req">שם ההורה או האפוטרופוס</span><input type="text" id="parent_name"></label>' +
    '<label class="f"><span class="req">טלפון ההורה</span><input type="tel" id="parent_phone" inputmode="tel"></label>';
  decl.appendChild(el("p", { class: "pol wait", id: "minor-note", hidden: "" },
    "מתחת לגיל 18: הורה או אפוטרופוס חותם/ת על הטופס ומגיע/ה לטיפול."));
  decl.appendChild(minor);
  var sig = el("div", { class: "sig", id: "sig" });
  sig.innerHTML = '<div class="row"><span>חתימה באצבע או בעכבר</span><button type="button" class="btn btn-ghost" id="sig-clear">ניקוי</button></div><canvas id="sig-pad" aria-label="שטח חתימה"></canvas>';
  decl.appendChild(sig);
  root.appendChild(decl);

  var hp = el("div", { class: "hp", "aria-hidden": "true" });
  hp.innerHTML = '<label>אתר<input type="text" id="website" tabindex="-1" autocomplete="off"></label>';
  root.appendChild(hp);
  root.appendChild(el("p", { class: "err", id: "err", hidden: "", role: "alert" }));
  root.appendChild(el("button", { type: "submit", class: "btn btn-main", id: "send" }, "שליחת ההצהרה"));

  // ---------- התנהגות ----------
  function answer(id) {
    var r = root.querySelector('input[name="' + id + '"]:checked');
    return r ? r.value : "";
  }

  function allYesNo() {
    var out = [];
    F.sections.forEach(function (s) { if (s.type === "yesno") s.items.forEach(function (i) { out.push(i); }); });
    return out;
  }

  function flags() {
    var f = { doc: [], stop: [], wait: [], note: [] };
    allYesNo().forEach(function (i) {
      if (i.policy && answer(i.id) === "כן") f[i.policy].push(i.short || i.q);
    });
    F.sections.forEach(function (s) {
      if (s.type !== "checks") return;
      root.querySelectorAll('input[name="' + s.id + '"]:checked').forEach(function (c) {
        var p = c.getAttribute("data-policy");
        if (p) f[p].push(s.short + ": " + c.value);
      });
    });
    return f;
  }

  function renderSummary() {
    var f = flags();
    if (!f.stop.length && !f.doc.length && !f.wait.length) { summary.hidden = true; return; }
    summary.hidden = false;
    summary.className = "summary " + (f.stop.length ? "stop" : "doc");
    var h = "";
    if (f.stop.length) h += "<h3>הסרה בלייזר לא מתאימה במצב הזה</h3><ul><li>" + f.stop.join("</li><li>") + "</li></ul><p>אפשר לשלוח את הטופס. אחזור אלייך אישית.</p>";
    if (f.doc.length) h += "<h3>נדרש אישור רופא לפני הטיפול</h3><ul><li>" + f.doc.join("</li><li>") + "</li></ul><p>אחרי השליחה תקבל/י מכתב מוכן לרופא. אין להפסיק או לשנות אף תרופה בלי הוראת הרופא.</p>";
    if (f.wait.length) h += "<h3>ייתכן שנצטרך לדחות</h3><ul><li>" + f.wait.join("</li><li>") + "</li></ul>";
    summary.innerHTML = h;
  }

  root.addEventListener("change", function (e) {
    var t = e.target;
    if (t.type === "radio") {
      var yes = t.value === "כן";
      var d = document.getElementById(t.name + "-d");
      var p = document.getElementById(t.name + "-p");
      if (d) d.hidden = !yes;
      if (p) p.hidden = !yes;
      var q = document.getElementById("q-" + t.name);
      if (q) q.classList.remove("missing");
      renderSummary();
    }
    if (t.type === "checkbox") renderSummary();
    if (t.id === "birth") checkMinor();
  });

  function age() {
    var v = document.getElementById("birth").value;
    if (!v) return null;
    var b = new Date(v), n = new Date();
    var a = n.getFullYear() - b.getFullYear();
    if (n.getMonth() < b.getMonth() || (n.getMonth() === b.getMonth() && n.getDate() < b.getDate())) a--;
    return a;
  }
  function checkMinor() {
    var a = age(), m = a !== null && a < 18;
    document.getElementById("minor").hidden = !m;
    document.getElementById("minor-note").hidden = !m;
  }

  // ---------- חתימה ----------
  var pad = document.getElementById("sig-pad");
  var ctx = pad.getContext("2d");
  var drawing = false, signed = false, last = null;
  function sizePad() {
    var r = pad.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    pad.width = r.width * dpr; pad.height = r.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineWidth = 2.2; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#2b1d20";
    signed = false;
  }
  sizePad();
  window.addEventListener("resize", function () { if (!signed) sizePad(); });
  function pos(e) { var r = pad.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }
  pad.addEventListener("pointerdown", function (e) { drawing = true; last = pos(e); pad.setPointerCapture(e.pointerId); });
  pad.addEventListener("pointermove", function (e) {
    if (!drawing) return;
    var p = pos(e);
    ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke();
    last = p; signed = true; sig.classList.remove("missing");
  });
  ["pointerup", "pointercancel", "pointerleave"].forEach(function (n) { pad.addEventListener(n, function () { drawing = false; }); });
  document.getElementById("sig-clear").addEventListener("click", function () { ctx.clearRect(0, 0, pad.width, pad.height); signed = false; });

  // ---------- תמונות (מוקטנות בדפדפן לפני השליחה) ----------
  var photos = [];
  root.addEventListener("change", function (e) {
    if (e.target.type !== "file") return;
    var prev = document.getElementById(e.target.id + "-prev");
    photos = []; prev.innerHTML = "";
    Array.prototype.slice.call(e.target.files, 0, 3).forEach(function (file) {
      shrink(file, function (data) {
        photos.push(data);
        prev.appendChild(el("img", { src: data, alt: "צילום אריזת תרופה" }));
      });
    });
  });
  function shrink(file, cb) {
    var img = new Image(), url = URL.createObjectURL(file);
    img.onload = function () {
      var s = Math.min(1, 1280 / Math.max(img.width, img.height));
      var c = document.createElement("canvas");
      c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      cb(c.toDataURL("image/jpeg", 0.8));
    };
    img.src = url;
  }

  // ---------- בדיקות ----------
  function validId(id) {
    id = String(id).replace(/\D/g, "");
    if (id.length < 5 || id.length > 9) return false;
    id = ("000000000" + id).slice(-9);
    var sum = 0;
    for (var i = 0; i < 9; i++) { var d = Number(id[i]) * ((i % 2) + 1); sum += d > 9 ? d - 9 : d; }
    return sum % 10 === 0;
  }
  function validPhone(p) { return /^0(5\d|[2-489]|7\d)\d{7}$/.test(String(p).replace(/\D/g, "")); }

  function validate() {
    var errs = [], first = null;
    function bad(node, msg) { errs.push(msg); if (!first) first = node; }
    F.sections.forEach(function (s) {
      if (s.type === "fields") s.fields.forEach(function (f) {
        var n = document.getElementById(f.id);
        if (f.required && !n.value.trim()) bad(n, "חסר: " + f.label);
      });
      if (s.type === "yesno") s.items.forEach(function (i) {
        if (!answer(i.id)) { var q = document.getElementById("q-" + i.id); q.classList.add("missing"); bad(q, "יש לענות על כל שאלות כן/לא"); }
      });
    });
    var idn = document.getElementById("id_number");
    if (idn.value.trim() && !validId(idn.value)) bad(idn, "מספר תעודת הזהות לא תקין");
    var ph = document.getElementById("phone");
    if (ph.value.trim() && !validPhone(ph.value)) bad(ph, "מספר הטלפון לא תקין");
    var a = age();
    if (a !== null && a < 18) {
      ["parent_name", "parent_phone"].forEach(function (id) {
        var n = document.getElementById(id); if (!n.value.trim()) bad(n, "מתחת לגיל 18 נדרשים פרטי הורה");
      });
    }
    F.agreements.forEach(function (_, i) {
      var c = document.getElementById("agree-" + i), l = document.getElementById("ag-" + i);
      l.classList.toggle("missing", !c.checked);
      if (!c.checked) bad(l, "יש לאשר את כל סעיפי ההצהרה");
    });
    if (!signed) { sig.classList.add("missing"); bad(sig, "חסרה חתימה"); }
    return { errs: errs.filter(function (v, i, a) { return a.indexOf(v) === i; }), first: first };
  }

  // ---------- איסוף ושליחה ----------
  function collect() {
    var client = {};
    F.sections.forEach(function (s) {
      if (s.type === "fields") s.fields.forEach(function (f) { client[f.id] = document.getElementById(f.id).value.trim(); });
    });
    var sections = [];
    F.sections.forEach(function (s) {
      if (s.type === "fields") {
        sections.push({ title: s.title, rows: s.fields.map(function (f) { return { label: f.label, answer: client[f.id] || "—" }; }) });
      }
      if (s.type === "yesno") {
        sections.push({ title: s.title, rows: s.items.map(function (i) {
          var a = answer(i.id);
          return { label: i.q, answer: a, detail: a === "כן" ? document.getElementById(i.id + "-d").value.trim() : "", policy: a === "כן" ? (i.policy || "") : "" };
        }) });
      }
      if (s.type === "checks") {
        var picked = [];
        root.querySelectorAll('input[name="' + s.id + '"]:checked').forEach(function (c) { picked.push(c.value); });
        sections.push({ title: s.title, rows: [{ label: "סומן", answer: picked.join(", ") || "אין", detail: document.getElementById(s.id + "-d").value.trim() }] });
      }
      (s.extra || []).forEach(function (x) {
        if (x.type === "textarea") sections[sections.length - 1].rows.push({ label: x.label, answer: document.getElementById(x.id).value.trim() || "—" });
      });
    });
    var a = age();
    return {
      service: F.service, serviceTitle: F.title, version: F.version,
      client: {
        name: client.full_name, phone: client.phone, idNumber: client.id_number, birth: client.birth, email: client.email || "",
        age: a, parentName: a !== null && a < 18 ? document.getElementById("parent_name").value.trim() : "",
        parentPhone: a !== null && a < 18 ? document.getElementById("parent_phone").value.trim() : ""
      },
      sections: sections, flags: flags(),
      declaration: F.declaration, agreements: F.agreements,
      signature: pad.toDataURL("image/png"), photos: photos,
      website: document.getElementById("website").value,
      userAgent: navigator.userAgent
    };
  }

  var errBox = document.getElementById("err");
  root.addEventListener("submit", function (e) {
    e.preventDefault();
    errBox.hidden = true;
    var v = validate();
    if (v.errs.length) {
      errBox.innerHTML = v.errs.join("<br>"); errBox.hidden = false;
      if (v.first) v.first.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (!window.PARDO_FORMS_ENDPOINT) {
      errBox.textContent = "הטופס עוד לא מחובר לשמירה. נא לשלוח הודעה לסטודיו."; errBox.hidden = false; return;
    }
    var btn = document.getElementById("send");
    btn.disabled = true; btn.textContent = "שולח/ת...";
    var data = collect();
    fetch(window.PARDO_FORMS_ENDPOINT, { method: "POST", body: JSON.stringify(data) })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.error || "save failed");
        showDone(data.flags);
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = "שליחת ההצהרה";
        errBox.innerHTML = "השליחה לא הצליחה. כדאי לבדוק את החיבור ולנסות שוב. אם זה חוזר, נא לשלוח הודעה בוואטסאפ: " +
          '<a href="https://wa.me/' + window.PARDO_WHATSAPP + '">055-284-5920</a>';
        errBox.hidden = false;
      });
  });

  function showDone(f) {
    root.hidden = true;
    var d = document.getElementById("done");
    var h = "<h2>ההצהרה התקבלה</h2><p>תודה. היא נשמרה בתיק שלך בסטודיו.</p>";
    if (f.stop.length) h += "<p>לפי התשובות, הסרה בלייזר לא מתאימה כרגע. אחזור אלייך אישית.</p>";
    else if (f.doc.length) h += '<p><b>לפני הטיפול נדרש אישור רופא.</b> הנה מכתב מוכן לרופא/ה המטפל/ת. אפשר להדפיס או להציג מהטלפון.</p><p><a class="btn btn-main" href="' + F.doctorLetter + '">למכתב לרופא</a></p>';
    if (f.wait.length && !f.stop.length) h += "<p>ייתכן שנצטרך לדחות את מועד הטיפול. נתאם יחד.</p>";
    h += '<p class="foot">שאלות? <a href="https://wa.me/' + window.PARDO_WHATSAPP + '">וואטסאפ 055-284-5920</a></p>';
    d.innerHTML = h; d.hidden = false;
    window.scrollTo(0, 0);
  }
})();
