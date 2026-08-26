/* Meta Pixel — PARDO Ink Art · מזהה 4439897412968454
   מדווח על שתי פעולות שמעניינות אותנו, מעבר לצפייה בעמוד:
     Contact — לחיצה על כפתור וואטסאפ כלשהו באתר
     Lead    — שליחת טופס יצירת הקשר בדף הבית (פנייה מפורטת, ליד חם יותר) */
!function (f, b, e, v, n, t, s) {
    if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments) };
    if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = []; t = b.createElement(e); t.async = !0;
    t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s)
}(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');

fbq('init', '4439897412968454');
fbq('track', 'PageView');

// כל קישור wa.me בכל הדפים. מאזין ברמת המסמך כדי לתפוס גם כפתורים שנוספים אחרי הטעינה.
document.addEventListener('click', function (e) {
    var link = e.target && e.target.closest && e.target.closest('a[href*="wa.me"]');
    if (link) fbq('track', 'Contact', { content_name: location.pathname });
}, true);

// טופס יצירת הקשר בדף הבית. שלב ה-capture כדי לרוץ לפני ה-preventDefault של הטופס עצמו.
document.addEventListener('submit', function (e) {
    if (e.target && e.target.id === 'contact-form') {
        var service = document.getElementById('cf-service');
        fbq('track', 'Lead', { content_name: service ? service.value : '' });
    }
}, true);
