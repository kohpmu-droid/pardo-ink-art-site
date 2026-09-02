#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שלב 3: מוריד את המקור למחשב ומפנה את הדרייב. רץ מקומית, מתי שנוח.

עובר על תת-התיקיות "פורסם" שבדרייב, מוריד כל קובץ בגודל המלא אל
F:\\תוכן\\תמונות לאתר\\<קטגוריה>, מוודא שהקובץ נשמר שלם — ורק אז שולח את
העותק שבדרייב לפח.

הדרייב הוא תיבת דואר נכנס: מה שפורסם ונשמר במחשב לא צריך להישאר שם. הקובץ
בפח ניתן לשחזור 30 יום, והמקור המלא כבר על הדיסק.

  python tools/archive_to_disk.py            # מוריד, מוודא ומפנה
  python tools/archive_to_disk.py --dry-run  # רק מראה מה היה קורה

יעד ברירת המחדל ניתן לשינוי במשתנה הסביבה GALLERY_ARCHIVE_DIR.
"""

import hashlib
import os
import sys
from pathlib import Path

from gdrive_client import (ARCHIVE_FOLDER, CATEGORIES, access_token, download,
                           find_or_create_folder, list_folder, load_env, trash)

DEFAULT_DIR = r"F:\תוכן\תמונות לאתר"


def target_dir():
    load_env()
    base = Path(os.environ.get("GALLERY_ARCHIVE_DIR", DEFAULT_DIR))
    if not base.exists():
        sys.exit("תיקיית היעד לא נמצאה: %s\n"
                 "אם הדיסק לא מחובר — כדאי פשוט להריץ מאוחר יותר." % base)
    return base


def already_saved(folder, size, md5):
    """קובץ זהה שכבר יושב בתיקייה — גם אם שמו שונה. מונע הורדה כפולה."""
    if not size:
        return None
    for path in folder.iterdir():
        if not path.is_file() or path.stat().st_size != size:
            continue
        if md5 is None or hashlib.md5(path.read_bytes()).hexdigest() == md5:
            return path
    return None


def unique_path(folder, name):
    """שם פנוי בתיקייה, כדי לא לדרוס קובץ ותיק ששמו זהה."""
    dest = folder / name
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for n in range(2, 100):
        candidate = folder / ("%s (%d)%s" % (stem, n, suffix))
        if not candidate.exists():
            return candidate
    return folder / ("%s (%d)%s" % (stem, os.getpid(), suffix))


def archive_category(token, key, cfg, base, dry_run):
    archive_id = find_or_create_folder(token, cfg["folder_id"], ARCHIVE_FOLDER)
    files = list_folder(token, archive_id, images_only=False)
    if not files:
        print("[%s] אין מה להוריד" % key)
        return 0

    folder = base / cfg["drive_name"]
    folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    for f in files:
        expected = int(f.get("size") or 0)
        existing = already_saved(folder, expected, f.get("md5Checksum"))
        if existing:
            print("[%s] %s כבר על הדיסק (%s)" % (key, f["name"], existing.name))
        else:
            if dry_run:
                print("[%s] היה יורד: %s" % (key, f["name"]))
                continue
            raw = download(token, f["id"])
            if expected and len(raw) != expected:
                print("[%s] הורדה חלקית של %s — משאירים בדרייב" % (key, f["name"]))
                continue
            dest = unique_path(folder, f["name"])
            dest.write_bytes(raw)
            print("[%s] %s <- %.1fMB" % (key, dest.name, len(raw) / 1048576))
        if dry_run:
            continue
        trash(token, f["id"])
        saved += 1
    return saved


def main():
    dry_run = "--dry-run" in sys.argv
    base = target_dir()
    token = access_token()
    total = sum(archive_category(token, key, cfg, base, dry_run)
                for key, cfg in CATEGORIES.items())
    if dry_run:
        print("הרצה יבשה — לא ירד ולא נמחק כלום")
    else:
        print("סה\"כ ירדו למחשב ונשלחו לפח בדרייב: %d" % total)


if __name__ == "__main__":
    main()
