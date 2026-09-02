#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שלב 1: מושך תמונות חדשות מגוגל דרייב אל גלריות האתר.

סורק שלוש תתי-תיקיות ב-Drive (קעקועים / פירסינג / הסרה בלייזר), מוריד כל תמונה
שעוד לא פורסמה, מקטין ודוחס אותה, ומוסיף אותה בראש הגלריה המתאימה.

הסקריפט לא נוגע בדרייב — הוא רק קורא. ניקוי הדרייב קורה רק אחרי שהשינוי מוזג
לאתר, ב-archive_drive_images.py.

מה שכבר פורסם נשמר ב-images/.gallery_state.json לפי מזהה הקובץ ב-Drive, כך ששינוי שם
בדרייב לא יגרום להעלאה כפולה, ומחיקה מהדרייב לא מוחקת מהאתר.

משתני סביבה נדרשים: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN
"""

import io
import re

from PIL import Image, ImageOps

try:  # תמונות iPhone נשמרות לפעמים כ-HEIF גם כשהסיומת jpg
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

from gdrive_client import (CATEGORIES, ROOT, access_token, download, list_folder,
                           load_state, save_state)

MAX_EDGE = 1400  # הצלע הארוכה בפיקסלים — הגלריה מציגה ריבועים קטנים
JPEG_QUALITY = 82

BLOCK_START = "/* AUTO-GALLERY-START */"
BLOCK_END = "/* AUTO-GALLERY-END */"


# ---------- עיבוד תמונה ----------

def save_web_jpeg(raw, dest):
    """מקטין, מיישר לפי EXIF, מסיר מטא-דאטה ושומר כ-JPEG קליל."""
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if max(img.size) > MAX_EDGE:
        img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def next_index(images_dir, prefix):
    """המספר הפנוי הבא, לפי הקבצים שכבר על הדיסק — כדי לא לדרוס תמונה ותיקה."""
    highest = 0
    if images_dir.exists():
        for f in images_dir.glob("%s*.jpg" % prefix):
            m = re.fullmatch(r"%s(\d+)" % re.escape(prefix), f.stem)
            if m:
                highest = max(highest, int(m.group(1)))
    return highest + 1


# ---------- עמוד הגלריה ----------

def read_block(page_text):
    """רשימת התמונות הקיימת בעמוד, כ-[[שם, alt], ...]."""
    m = re.search(re.escape(BLOCK_START) + r"(.*?)" + re.escape(BLOCK_END),
                  page_text, re.S)
    if not m:
        return None
    body = m.group(1)
    pairs = re.findall(r'\[\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\]', body)
    return [list(p) for p in pairs]


def write_block(page_text, entries):
    lines = ",\n".join(
        '                ["%s", "%s"]' % (name, alt.replace('"', "'"))
        for name, alt in entries
    )
    block = "%s\n            var images = [\n%s\n            ];\n            %s" % (
        BLOCK_START, lines, BLOCK_END)
    return re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END),
                  lambda _: block, page_text, flags=re.S)


# שמות שהמצלמה או וואטסאפ נתנו — אין בהם שום מידע על התמונה
GENERIC_NAME = re.compile(r"""^(
      \d{6,}                                   # 1000449758
    | \d{8}[_-]\d{4,6}(\(\d+\))?               # 20260823_122657
    | (IMG|VID|PXL|DSC|DCIM|PANO|MVIMG|lv)[-_ ].*
    | (WhatsApp|Screenshot|Snapchat|Facebook|Instagram|image|photo|תמונה)\b.*
    | [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-.*   # uuid
)$""", re.I | re.X)


def clean_alt(drive_name):
    """שם הקובץ בדרייב הופך לטקסט חלופי — טוב לנגישות ולגוגל.

    שם גנרי של מצלמה לא מתאר כלום, ו-alt כמו "1000449758" גרוע יותר מאשר כלום:
    קורא מסך יקריא אותו, וגוגל יראה רעש. במקרה כזה מחזירים מחרוזת ריקה, והעמוד
    נופל לטקסט ברירת המחדל שלו.
    """
    stem = re.sub(r"\.(jpe?g|png|heic|heif|webp)$", "", drive_name, flags=re.I)
    if GENERIC_NAME.match(stem.strip()):
        return ""
    alt = re.sub(r"[_\-]+", " ", stem)
    alt = re.sub(r"\s+", " ", alt).strip()
    return alt[:90]


# ---------- ראשי ----------

def sync_category(token, key, cfg, state):
    page_path = ROOT / cfg["page"]
    if not page_path.exists():
        print("[%s] אין עמוד %s — מדלגים" % (key, cfg["page"]))
        return 0

    page_text = page_path.read_text(encoding="utf-8")
    entries = read_block(page_text)
    if entries is None:
        print("[%s] לא נמצא בלוק AUTO-GALLERY ב-%s — מדלגים" % (key, cfg["page"]))
        return 0

    known = state.setdefault(key, {})
    remote = list_folder(token, cfg["folder_id"])
    new_files = [f for f in remote if f["id"] not in known]
    if not new_files:
        print("[%s] אין תמונות חדשות (%d בתיקייה)" % (key, len(remote)))
        return 0

    images_dir = ROOT / cfg["images_dir"]
    index = next_index(images_dir, cfg["prefix"])
    added = []
    for f in new_files:
        name = "%s%02d" % (cfg["prefix"], index)
        try:
            save_web_jpeg(download(token, f["id"]), images_dir / ("%s.jpg" % name))
        except Exception as exc:  # תמונה פגומה לא תפיל את כל הריצה
            print("[%s] דילוג על %s: %s" % (key, f["name"], exc))
            continue
        alt = clean_alt(f["name"])
        # archived=false: התמונה עוד יושבת בתיקייה הראשית בדרייב וממתינה לניקוי
        known[f["id"]] = {"file": name, "title": f["name"], "archived": False}
        added.append([name, alt])
        print("[%s] %s <- %s" % (key, name, f["name"]))
        if not alt:
            # מסומן כדי שיופיע ב-PR: תמונה בלי תיאור מפסידה תנועה מגוגל תמונות
            print("NEEDS-NAME: %s (%s) — שם גנרי בדרייב, אין ממה לגזור תיאור"
                  % (name, f["name"]))
        index += 1

    if not added:
        return 0

    # החדשות בראש הגלריה, החדשה ביותר ראשונה
    entries = list(reversed(added)) + entries
    page_path.write_text(write_block(page_text, entries), encoding="utf-8")
    return len(added)


def main():
    token = access_token()
    state = load_state()
    total = sum(sync_category(token, key, cfg, state)
                for key, cfg in CATEGORIES.items())
    if total:
        save_state(state)
    print("סה\"כ תמונות שנוספו: %d" % total)


if __name__ == "__main__":
    main()
