# -*- coding: utf-8 -*-
"""Publish ONE queued article per run — fully self-contained, NO credentials.
Reads pre-exported content from content/meta/*.json + content/bodies/<slug>,
picks the earliest-dated article that is not yet live (its <slug> file does not
exist in the repo root), renders the full page, and adds a card to articles.html.
Runs in GitHub Actions. Exit 0 always (commit decided by git status)."""
import glob, json, html, datetime, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

TATTOO_KW = "קעקועים בכרמי גת, קעקועים בקריית גת, קעקועים בדרום, מקעקעת בקריית גת, קעקועי פיין ליין, מיקרו ריאליזם, פרדו אינק ארט"
PIERCE_KW = "פירסינג בכרמי גת, פירסינג בקריית גת, פירסינג בדרום, פירסר בקריית גת, עיצובי אוזניים, פירסינג ילדים, פרדו אינק ארט"
TATTOO_SEO = 'פרדו אינק ארט — <strong>קעקועים בכרמי גת</strong>, קעקועים בקריית גת וקעקועים בדרום. קליניקת בוטיק לקעקועי פיין ליין ומיקרו ריאליזם, בתיאום מראש.'
PIERCE_SEO = 'פרדו אינק ארט — <strong>פירסינג בכרמי גת</strong>, פירסינג בקריית גת ופירסינג בדרום. פירסינג מקצועי בכל הגוף, עיצובי אוזניים ופירסינג ילדים ותינוקות, בתיאום מראש.'

TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Pardo Ink Art</title>
    <meta name="description" content="{meta}">
    <meta name="keywords" content="{keywords}">
    <link rel="icon" type="image/svg+xml" href="logo.svg">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;500;600;700&family=Frank+Ruhl+Libre:wght@400;500;700;900&family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/js/all.min.js"></script>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <nav class="sticky top-0 w-full z-50 bg-[#f7f2ea]/90 backdrop-blur-md border-b border-[#b79891]/25">
        <div class="max-w-4xl mx-auto px-4"><div class="flex items-center justify-between h-20">
            <a href="index.html" class="flex items-center gap-3"><img src="logo.svg" alt="Pardo Ink Art" class="h-14 w-14 object-contain"><span class="text-lg font-bold brand-serif accent-wine hidden sm:block">פרדו אינק ארט</span></a>
            <a href="articles.html" class="btn-outline px-5 py-2 rounded-full text-sm font-semibold inline-flex items-center gap-2"><i class="fas fa-arrow-right"></i> לכל המאמרים</a>
        </div></div>
    </nav>
    <main class="content max-w-3xl mx-auto px-4 py-14">
        <a href="articles.html" class="accent-wine text-sm">&#8594; חזרה למאמרים</a>
        <p class="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p class="meta">מאת כוכבית פרדו · פורסם {date_he}</p>
{body}
        <p class="text-sm mt-6" style="color:var(--muted)">{seo}</p>

        <div class="text-center mt-14"><a href="https://wa.me/972506225490" target="_blank" rel="noopener" class="btn-wine inline-flex items-center gap-2 px-8 py-4 rounded-full text-lg font-semibold"><i class="fab fa-whatsapp"></i> {cta}</a></div>
    </main>
    <footer class="bg-wine py-10 text-center text-[#f3e7e0]">
        <div class="max-w-4xl mx-auto px-4">
            <p class="brand-serif text-lg font-bold mb-1">פרדו אינק ארט</p>
            <p class="text-sm text-[#e6cfc7] mb-4">קעקועים ופירסינג בכרמי גת / קריית גת · <a href="tel:+972506225490" class="underline hover:text-white">050-622-5490</a></p>
            <div class="flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm mb-3">
                <a href="index.html" class="text-[#e6cfc7] underline hover:text-white">דף הבית</a>
                <a href="articles.html" class="text-[#e6cfc7] underline hover:text-white">מאמרים</a>
                <a href="{gallery}" class="text-[#e6cfc7] underline hover:text-white">{gallery_he}</a>
            </div>
            <div class="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs mb-3">
                <a href="privacy.html" class="text-[#d8b9b0] underline hover:text-white">מדיניות פרטיות</a>
                <a href="accessibility.html" class="text-[#d8b9b0] underline hover:text-white">הצהרת נגישות</a>
                <a href="terms.html" class="text-[#d8b9b0] underline hover:text-white">תקנון האתר</a>
            </div>
            <p class="text-[11px] text-[#d8b9b0]">© 2026 Pardo Ink Art · כל הזכויות שמורות</p>
        </div>
    </footer>
    <script src="a11y.js" defer></script>
</body>
</html>
"""

def render(d, body_html):
    piercing = (d["field"] == "פירסינג")
    return TEMPLATE.format(
        title=html.escape(d["title"]),
        meta=html.escape(d["meta"]),
        keywords=PIERCE_KW if piercing else TATTOO_KW,
        eyebrow=d["field"],
        date_he=datetime.date.today().strftime("%d.%m.%Y"),
        body=body_html,
        seo=PIERCE_SEO if piercing else TATTOO_SEO,
        cta="לתיאום פירסינג" if piercing else "לשאלה או תיאום קעקוע",
        gallery="piercing.html" if piercing else "gallery.html",
        gallery_he="גלריית פירסינג" if piercing else "גלריית קעקועים",
    )

def add_card(ah, field, slug, title, short):
    cat = "cat-piercing" if field == "פירסינג" else "cat-tattoo"
    latin = "PIERCING" if field == "פירסינג" else "TATTOO"
    card = (
        '                <a href="%s" class="article-card">\n'
        '                    <span class="latin text-xs text-[var(--mauve)]">%s</span>\n'
        '                    <h3 class="text-xl font-bold accent-wine mb-2">%s</h3>\n'
        '                    <p class="text-[var(--muted)] leading-relaxed">%s</p>\n'
        '                    <span class="accent-wine font-semibold text-sm mt-3 inline-block">קראו עוד &#8592;</span>\n'
        '                </a>\n'
        % (html.escape(slug), latin, html.escape(title), html.escape(short))
    )
    m = re.search(r'id="%s"' % cat, ah)
    if not m:
        raise RuntimeError("cat container not found: " + cat)
    gm = re.search(r'<div class="grid[^"]*"[^>]*>', ah[m.end():])
    if not gm:
        raise RuntimeError("grid not found for " + cat)
    pos = m.end() + gm.end()
    ah = ah[:pos] + "\n" + card + ah[pos:]
    tm = re.search(r"toggleCat\('%s'" % cat, ah)
    if tm:
        seg = ah[tm.end():tm.end() + 600]
        cm = re.search(r"(\d+) מאמרים", seg)
        if cm:
            seg2 = seg[:cm.start()] + ("%d מאמרים" % (int(cm.group(1)) + 1)) + seg[cm.end():]
            ah = ah[:tm.end()] + seg2 + ah[tm.end() + 600:]
    return ah

def main():
    metas = []
    for p in glob.glob(str(ROOT / "content" / "meta" / "*.json")):
        try:
            metas.append(json.load(open(p, encoding="utf-8")))
        except Exception as e:
            print("skip bad json %s: %s" % (p, e), file=sys.stderr)
    # candidates: not yet live + body present
    cands = []
    for d in metas:
        slug = d.get("slug", "")
        if not slug:
            continue
        if (ROOT / slug).exists():
            continue  # already published
        if not (ROOT / "content" / "bodies" / slug).exists():
            continue
        cands.append(d)
    if not cands:
        print("NO CHANGE: queue exhausted (nothing left to publish)")
        return 0
    cands.sort(key=lambda d: (d.get("date", "9999-99-99"), d["slug"]))
    d = cands[0]
    slug = d["slug"]
    body_html = (ROOT / "content" / "bodies" / slug).read_text(encoding="utf-8").rstrip("\n")
    (ROOT / slug).write_text(render(d, body_html), encoding="utf-8")
    ah = (ROOT / "articles.html").read_text(encoding="utf-8")
    ah = add_card(ah, d["field"], slug, d["title"], d["short"])
    (ROOT / "articles.html").write_text(ah, encoding="utf-8")
    print("PUBLISHED: [%s] %s -> %s (%d left in queue)" % (d["field"], d["title"], slug, len(cands) - 1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
