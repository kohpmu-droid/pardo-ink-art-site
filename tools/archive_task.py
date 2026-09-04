#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
"""עטיפה למשימה המתוזמנת של Windows: מריצה את הגיבוי ל-F: בלי חלון ולתוך יומן.

מופעלת על ידי Task Scheduler עם pythonw.exe, ולכן אין לה מסך להדפיס אליו —
הכל נכתב ל-%LOCALAPPDATA%\\pardo-gallery-archive.log. את היומן אפשר לפתוח
בפנקס רשימות כדי לראות מה קרה בריצות האחרונות.

להרצה ידנית עם פלט למסך: python tools/archive_to_disk.py
"""

import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LOG = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "pardo-gallery-archive.log"
MAX_LOG_BYTES = 200_000


def trim(path):
    """יומן שגדל בלי סוף הוא באג — משאירים את החצי האחרון."""
    try:
        if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
            tail = path.read_bytes()[-MAX_LOG_BYTES // 2:]
            path.write_bytes(b"...\n" + tail)
    except OSError:
        pass


def main():
    trim(LOG)
    with open(LOG, "a", encoding="utf-8", errors="replace") as log:
        sys.stdout = sys.stderr = log
        stamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        print("\n=== %s ===" % stamp)
        try:
            import archive_to_disk
            archive_to_disk.main()
        except SystemExit as exc:      # הדיסק לא מחובר, למשל — לא כישלון אמיתי
            print("עצירה: %s" % exc)
        except Exception as exc:
            print("שגיאה: %r" % exc)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
