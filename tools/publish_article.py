# -*- coding: utf-8 -*-
"""Publish ONE queued article/day to the Pardo Ink Art site, driven by the
Notion "מאמרים לאתר" database. Runs in GitHub Actions.

Flow: pick today's field (opposite of last-published, alternating) -> take the
oldest queued ("מתוזמן") article of that field -> fetch its body blocks ->
build the article HTML from the template -> add a card to articles.html ->
mark the Notion row "פורסם באתר" with today's date + live URL.

Requires env NOTION_TOKEN (a Notion internal integration token with access to
the database). Exit 10 = published (repo changed), 0 = nothing to publish,
1 = error.
"""
import os, re, sys, json, html, datetime, urllib.request, urllib.error, pathlib

TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
DB_ID = "8c1d4e9b0d464dad85c2ed6bc6d7135b"           # "מאמרים לאתר" database
SITE_BASE = "https://kohpmu-droid.github.io/pardo-ink-art-site/"
ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

AUTHORITIES = [
    ("World Health Organization", "https://www.who.int"),
    ("American Academy of Dermatology", "https://www.aad.org"),
    ("Association of Professional Piercers", "https://safepiercing.org"),
    ("Skin Cancer Foundation", "https://www.skincancer.org"),
    ("Mayo Clinic", "https://www.mayoclinic.org"),
    ("Magen David Adom", "https://www.mdais.org"),
    ('מד"א', "https://www.mdais.org"),
    ("משרד הבריאות", "https://www.gov.il/he/departments/ministry_of_health"),
    ("ACOG", "https://www.acog.org"),
    ("NHS", "https://www.nhs.uk"),
    ("CDC", "https://www.cdc.gov"),
    ("FDA", "https://www.fda.gov"),
    ("WHO", "https://www.who.int"),
    ("AAD", "https://www.aad.org"),
    ("APP", "https://safepiercing.org"),
]

# ---------- Notion API helpers ----------

def api(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("Notion API error %s on %s %s: %s" % (e.code, method, path, e.read().decode("utf-8", "replace")), file=sys.stderr)
        raise

def query_db(status, field=None, by_created=True):
    conds = [
        {"property": "סטטוס", "select": {"equals": status}},
        {"property": "סוג", "select": {"equals": "מאמר"}},
    ]
    if field:
        conds.append({"property": "תחום", "select": {"equals": field}})
    body = {"filter": {"and": conds}, "page_size": 1}
    if by_created:
        body["sorts"] = [{"timestamp": "created_time", "direction": "ascending"}]
    else:
        body["sorts"] = [{"property": "תאריך פרסום", "direction": "descending"}]
    return api("POST", "/databases/%s/query" % DB_ID, body)["results"]

def prop_title(page, name):
    arr = page["properties"][name]["title"]
    return "".join(t["plain_text"] for t in arr).strip()

def prop_text(page, name):
    arr = page["properties"][name].get("rich_text", [])
    return "".join(t["plain_text"] for t in arr).strip()

def prop_select(page, name):
    s = page["properties"][name].get("select")
    return s["name"] if s else None

def get_blocks(block_id):
    out, cursor = [], None
    while True:
        q = "?page_size=100" + (("&start_cursor=" + cursor) if cursor else "")
        res = api("GET", "/blocks/%s/children%s" % (block_id, q))
        out.extend(res["results"])
        if res.get("has_more"):
            cursor = res["next_cursor"]
        else:
            break
    return out

# ---------- block -> HTML ----------

def rich_to_html(rich):
    parts = []
    for t in rich:
        txt = html.escape(t.get("plain_text", ""))
        ann = t.get("annotations", {})
        if ann.get("bold"):
            txt = "<strong>%s</strong>" % txt
        if ann.get("italic"):
            txt = "<em>%s</em>" % txt
        href = t.get("href")
        if href:
            txt = '<a href="%s" target="_blank" rel="noopener nofollow">%s</a>' % (html.escape(href), txt)
        parts.append(txt)
    return "".join(parts)

def blocks_to_html(blocks):
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        t = b["type"]
        if t == "paragraph":
            txt = rich_to_html(b["paragraph"]["rich_text"])
            if txt.strip():
                out.append("        <p>%s</p>" % txt)
        elif t == "heading_2":
            out.append("        <h2>%s</h2>" % rich_to_html(b["heading_2"]["rich_text"]))
        elif t == "heading_3":
            out.append("        <h3>%s</h3>" % rich_to_html(b["heading_3"]["rich_text"]))
        elif t == "quote":
            out.append("        <blockquote>%s</blockquote>" % rich_to_html(b["quote"]["rich_text"]))
        elif t == "divider":
            pass
        elif t == "bulleted_list_item" or t == "numbered_list_item":
            tag = "ul" if t == "bulleted_list_item" else "ol"
            items = []
            while i < len(blocks) and blocks[i]["type"] == t:
                items.append("            <li>%s</li>" % rich_to_html(blocks[i][t]["rich_text"]))
                i += 1
            out.append("        <%s>\n%s\n        </%s>" % (tag, "\n".join(items), tag))
            continue
        elif t == "table":
            rows = get_blocks(b["id"])
            trs = []
            for ri, row in enumerate(rows):
                if row["type"] != "table_row":
                    continue
                cells = row["table_row"]["cells"]
                tag = "th" if ri == 0 else "td"
                tds = "".join("<%s>%s</%s>" % (tag, rich_to_html(c), tag) for c in cells)
                trs.append("<tr>%s</tr>" % tds)
            out.append('        <div style="overflow-x:auto"><table>%s</table></div>' % "".join(trs))
        i += 1
    body = "\n".join(out)
    return linkify_authorities(body)

def linkify_authorities(body):
    for name, url in AUTHORITIES:
        # only linkify names that are not already inside an anchor
        pattern = re.compile(r'(?<![">/\w])' + re.escape(name) + r'(?![^<]*</a>)')
        link = '<a href="%s" target="_blank" rel="noopener nofollow">%s</a>' % (url, name)
        body = pattern.sub(link, body, count=1)
    return body

# ---------- article page + articles.html ----------

def first_sentence(blocks, maxlen):
    for b in blocks:
        if b["type"] == "paragraph":
            txt = "".join(t.get("plain_text", "") for t in b["paragraph"]["rich_text"]).strip()
            if txt:
                return (txt[:maxlen]).rsplit(" ", 1)[0] if len(txt) > maxlen else txt
    return ""

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

TATTOO_KW = "קעקועים בכרמי גת, קעקועים בקריית גת, קעקועים בדרום, מקעקעת בקריית גת, קעקועי פיין ליין, מיקרו ריאליזם, פרדו אינק ארט"
PIERCE_KW = "פירסינג בכרמי גת, פירסינג בקריית גת, פירסינג בדרום, פירסר בקריית גת, עיצובי אוזניים, פירסינג ילדים, פרדו אינק ארט"
TATTOO_SEO = 'פרדו אינק ארט — <strong>קעקועים בכרמי גת</strong>, קעקועים בקריית גת וקעקועים בדרום. קליניקת בוטיק לקעקועי פיין ליין ומיקרו ריאליזם, בתיאום מראש.'
PIERCE_SEO = 'פרדו אינק ארט — <strong>פירסינג בכרמי גת</strong>, פירסינג בקריית גת ופירסינג בדרום. פירסינג מקצועי בכל הגוף, עיצובי אוזניים ופירסינג ילדים ותינוקות, בתיאום מראש.'

HE_MONTHS = None

def build_article_html(title, field, body_html, meta, date_he):
    piercing = (field == "פירסינג")
    return TEMPLATE.format(
        title=html.escape(title),
        meta=html.escape(meta),
        keywords=PIERCE_KW if piercing else TATTOO_KW,
        eyebrow=field,
        date_he=date_he,
        body=body_html,
        seo=PIERCE_SEO if piercing else TATTOO_SEO,
        cta="לתיאום פירסינג" if piercing else "לשאלה או תיאום קעקוע",
        gallery="piercing.html" if piercing else "gallery.html",
        gallery_he="גלריית פירסינג" if piercing else "גלריית קעקועים",
    )

def add_card(articles_html, field, slug, title, short):
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
    # insert card right after the grid opening inside the category container
    m = re.search(r'id="%s"' % cat, articles_html)
    if not m:
        raise RuntimeError("cat container not found: " + cat)
    gm = re.search(r'<div class="grid[^"]*"[^>]*>', articles_html[m.end():])
    if not gm:
        raise RuntimeError("grid not found for " + cat)
    pos = m.end() + gm.end()
    articles_html = articles_html[:pos] + "\n" + card + articles_html[pos:]
    # bump the "N מאמרים" counter in that category's toggle header
    tm = re.search(r"toggleCat\('%s'" % cat, articles_html)
    if tm:
        seg_start = tm.end()
        seg = articles_html[seg_start:seg_start + 600]
        cm = re.search(r"(\d+) מאמרים", seg)
        if cm:
            newnum = int(cm.group(1)) + 1
            seg2 = seg[:cm.start()] + "%d מאמרים" % newnum + seg[cm.end():]
            articles_html = articles_html[:seg_start] + seg2 + articles_html[seg_start + 600:]
    return articles_html

# ---------- main ----------

def main():
    if not TOKEN:
        print("ERROR: NOTION_TOKEN not set", file=sys.stderr)
        return 1
    # 1. today's field = opposite of last published
    last = query_db("פורסם באתר", by_created=False)
    last_field = prop_select(last[0], "תחום") if last else None
    field = "קעקועים" if last_field == "פירסינג" else "פירסינג" if last_field == "קעקועים" else \
            ("פירסינג" if datetime.date.today().day % 2 == 0 else "קעקועים")
    # 2. next queued of that field (fallback to other field)
    res = query_db("מתוזמן", field=field)
    if not res:
        other = "פירסינג" if field == "קעקועים" else "קעקועים"
        res = query_db("מתוזמן", field=other)
        field = other
    if not res:
        print("NO CHANGE: queue empty")
        return 0
    page = res[0]
    pid = page["id"]
    title = prop_title(page, "כותרת")
    slug = prop_text(page, "קובץ באתר")
    if not slug:
        print("ERROR: page has no slug (קובץ באתר): " + title, file=sys.stderr)
        return 1
    # 3. body
    blocks = get_blocks(pid)
    body_html = blocks_to_html(blocks)
    meta = first_sentence(blocks, 155)
    short = first_sentence(blocks, 120)
    today = datetime.date.today().isoformat()
    date_he = datetime.date.today().strftime("%d.%m.%Y")
    # 4. write article file
    (ROOT / slug).write_text(build_article_html(title, field, body_html, meta, date_he), encoding="utf-8")
    # 5. articles.html card + counter
    ah = (ROOT / "articles.html").read_text(encoding="utf-8")
    ah = add_card(ah, field, slug, title, short)
    (ROOT / "articles.html").write_text(ah, encoding="utf-8")
    # 6. mark the Notion row published (same page)
    url = SITE_BASE + slug
    api("PATCH", "/pages/" + pid, {"properties": {
        "סטטוס": {"select": {"name": "פורסם באתר"}},
        "קישור באתר": {"url": url},
        "תאריך פרסום": {"date": {"start": today}},
    }})
    print("PUBLISHED: [%s] %s -> %s" % (field, title, url))
    return 10

if __name__ == "__main__":
    sys.exit(main())
