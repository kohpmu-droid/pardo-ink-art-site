# -*- coding: utf-8 -*-
"""עטיפה דקה ל-Google Drive API + ההגדרות המשותפות לגלריות האתר.

כל הסקריפטים של הגלריה עובדים מול התיקייה בדרייב:
    אתר / תמונות לאתר / {קעקועים, פירסינג, הסרה בלייזר}
https://drive.google.com/drive/folders/1nq8uYmXYuUkPwv7ysY6avsN2alTzVcrO

תמונה שפורסמה עוברת לתת-תיקייה "פורסם" בתוך תיקיית הקטגוריה, כדי שהתיקייה
הראשית תישאר רשימת ה"עוד לא פורסם". משם היא יורדת לדיסק המקומי ונמחקת מהדרייב.

משתני סביבה: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN
(אפשר גם בקובץ .env בשורש הריפו — הוא לא נכנס לגיט).
"""

import json
import os
import sys
from pathlib import Path

import requests

try:  # קונסולת Windows לא תמיד יודעת לקודד כל תו — עדיף '?' מאשר ריצה שנופלת
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "images" / ".gallery_state.json"
ARCHIVE_FOLDER = "פורסם"

CATEGORIES = {
    "tattoo": {
        "folder_id": "1apDQXywYCO9IhWZLnTfLnAmuecGIWK7m",
        "drive_name": "קעקועים",
        "prefix": "g",
        "images_dir": "images/gallery",
        "page": "gallery.html",
    },
    "piercing": {
        "folder_id": "1LUYw7QVUoon_R-6koPOM4aNKac7dV-Kx",
        "drive_name": "פירסינג",
        "prefix": "p",
        "images_dir": "images/piercing",
        "page": "piercing.html",
    },
    "laser": {
        "folder_id": "1kFfZ96DpuyBFas-bqGpKwzjiJ7fo2fZm",
        "drive_name": "הסרה בלייזר",
        "prefix": "l",
        "images_dir": "images/laser",
        "page": "laser.html",
    },
}

IMAGE_MIMES = ("image/jpeg", "image/png", "image/heif", "image/heic", "image/webp")

API = "https://www.googleapis.com/drive/v3/files"


# ---------- סביבה ----------

def load_env():
    """טוען .env מהריפו אם קיים, בלי לדרוס משתנים שכבר הוגדרו."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def access_token():
    load_env()
    missing = [k for k in ("GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN")
               if not os.environ.get(k)]
    if missing:
        sys.exit("חסרים משתני סביבה: " + ", ".join(missing))
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GDRIVE_CLIENT_ID"],
        "client_secret": os.environ["GDRIVE_CLIENT_SECRET"],
        "refresh_token": os.environ["GDRIVE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    if not r.ok:
        sys.exit("החידוש של טוקן הגישה נכשל: %s %s" % (r.status_code, r.text[:300]))
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": "Bearer " + token}


# ---------- קריאה ----------

def list_folder(token, folder_id, images_only=True):
    """כל הקבצים שישירות בתיקייה, מהישן לחדש. תתי-תיקיות לא נסרקות."""
    files, page_token = [], None
    while True:
        params = {
            "q": "'%s' in parents and trashed = false" % folder_id,
            "fields": "nextPageToken, files(id, name, mimeType, size, md5Checksum, createdTime)",
            "orderBy": "createdTime",
            "pageSize": 200,
        }
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(API, params=params, headers=_headers(token), timeout=60)
        r.raise_for_status()
        data = r.json()
        for f in data.get("files", []):
            if not images_only or f["mimeType"] in IMAGE_MIMES:
                files.append(f)
        page_token = data.get("nextPageToken")
        if not page_token:
            return files


def download(token, file_id):
    r = requests.get("%s/%s" % (API, file_id), params={"alt": "media"},
                     headers=_headers(token), timeout=300)
    r.raise_for_status()
    return r.content


# ---------- כתיבה ----------

def find_or_create_folder(token, parent_id, name):
    """מזהה תת-התיקייה בשם הזה, ויוצר אותה אם אינה קיימת."""
    q = ("'%s' in parents and trashed = false and name = '%s' "
         "and mimeType = 'application/vnd.google-apps.folder'" % (parent_id, name))
    r = requests.get(API, params={"q": q, "fields": "files(id)"},
                     headers=_headers(token), timeout=60)
    r.raise_for_status()
    found = r.json().get("files", [])
    if found:
        return found[0]["id"]
    r = requests.post(API, headers=_headers(token), json={
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def move(token, file_id, from_parent, to_parent):
    r = requests.patch("%s/%s" % (API, file_id),
                       params={"addParents": to_parent, "removeParents": from_parent,
                               "fields": "id, parents"},
                       headers=_headers(token), timeout=60)
    r.raise_for_status()
    return r.json()


def trash(token, file_id):
    """לפח האשפה של הדרייב — הפיך במשך 30 יום, ולא מחיקה קבועה."""
    r = requests.patch("%s/%s" % (API, file_id), headers=_headers(token),
                       json={"trashed": True}, timeout=60)
    r.raise_for_status()


# ---------- מצב ----------

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            print("קובץ המצב פגום — מתחילים ממנו מחדש (תמונות קיימות לא ייפגעו)")
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
