#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שלב 2: מפנה מהדרייב את התמונות שכבר עלו לאתר.

רץ רק אחרי שהשינוי מוזג ל-main, כלומר אחרי שהתמונה באמת מוצגת בגלריה. כל תמונה
כזאת עוברת מתיקיית הקטגוריה לתת-התיקייה "פורסם" — כך שהתיקייה הראשית בדרייב
נשארת בדיוק רשימת מה שעוד לא פורסם.

התמונה עצמה עדיין בדרייב בשלב הזה. המחיקה קורית ב-archive_to_disk.py, ורק אחרי
שהקובץ המקורי נשמר על הדיסק המקומי.

משתני סביבה נדרשים: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN
"""

import sys

from gdrive_client import (ARCHIVE_FOLDER, CATEGORIES, ROOT, access_token,
                           find_or_create_folder, load_state, move, save_state)


def pending(state):
    """כל מה שפורסם ועדיין לא הועבר לתיקיית 'פורסם', לפי קטגוריה."""
    for key, cfg in CATEGORIES.items():
        for file_id, entry in state.get(key, {}).items():
            if not entry.get("archived"):
                yield key, cfg, file_id, entry


def main():
    state = load_state()
    todo = list(pending(state))
    if not todo:
        print("אין תמונות שממתינות לפינוי מהדרייב")
        return

    token = access_token()
    archive_ids = {}
    moved = 0
    for key, cfg, file_id, entry in todo:
        # רק תמונה שהקובץ שלה באמת יושב בריפו — ההגנה מפני פינוי מוקדם מדי
        image = ROOT / cfg["images_dir"] / ("%s.jpg" % entry["file"])
        if not image.exists():
            print("[%s] %s עוד לא בריפו — משאירים בדרייב" % (key, entry["file"]))
            continue
        if key not in archive_ids:
            archive_ids[key] = find_or_create_folder(token, cfg["folder_id"], ARCHIVE_FOLDER)
        try:
            move(token, file_id, cfg["folder_id"], archive_ids[key])
        except Exception as exc:  # קובץ שנמחק בינתיים ידנית לא יפיל את הריצה
            print("[%s] לא הצלחתי להעביר את %s: %s" % (key, entry["title"], exc))
            continue
        entry["archived"] = True
        moved += 1
        print("[%s] %s -> %s/%s" % (key, entry["title"], cfg["drive_name"], ARCHIVE_FOLDER))

    if moved:
        save_state(state)
    print("סה\"כ הועברו לתיקיית 'פורסם': %d" % moved)


if __name__ == "__main__":
    sys.exit(main())
