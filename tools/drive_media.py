# -*- coding: utf-8 -*-
"""מרכז החומרים בדרייב ↔ Claude.

    push <src_dir> <folder_id> [sub/path]   מעלה את כל הקבצים מתיקייה מקומית לתיקייה בדרייב
                                             (יוצר תתי-תיקיות לפי הצורך, לא מעלה פעמיים קובץ באותו שם)
    pull <folder_id> <out_dir>              מוריד את כל הסרטונים והתמונות מהתיקייה ומתתי-התיקיות שלה
                                             (סרטונים: עותק H.264 עד 1920 גובה), לפי מבנה התיקיות

ראו "🖤 מרכז חומרים" בדרייב: "1 · סרטונים לעריכה" (כוכבית מעלה) ו-"2 · מוכן לפרסום" (Claude מעלה).
משתני סביבה: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN
"""
import json
import mimetypes
import os
import subprocess
import sys

import requests

from gdrive_client import API, access_token, find_or_create_folder, list_folder

UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
VIDEO = ("video/",)
MEDIA = ("video/", "image/")


def _h(token):
    return {"Authorization": "Bearer " + token}


def children(token, folder_id):
    return list_folder(token, folder_id, images_only=False)


def upload(token, path, parent):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    meta = {"name": os.path.basename(path), "parents": [parent]}
    r = requests.post(UPLOAD, params={"uploadType": "resumable"}, headers={**_h(token),
                      "X-Upload-Content-Type": mime}, json=meta, timeout=60)
    r.raise_for_status()
    with open(path, "rb") as fh:
        r2 = requests.put(r.headers["Location"], data=fh, headers={"Content-Type": mime}, timeout=600)
    r2.raise_for_status()
    return r2.json()["id"]


def push(src, folder_id, sub=""):
    token = access_token()
    target = folder_id
    for part in [p for p in sub.split("/") if p]:
        target = find_or_create_folder(token, target, part)
    existing = {f["name"] for f in children(token, target)}
    n = 0
    for name in sorted(os.listdir(src)):
        p = os.path.join(src, name)
        if not os.path.isfile(p) or name.startswith("."):
            continue
        if name in existing:
            print("  כבר קיים, מדלגת: " + name)
            continue
        fid = upload(token, p, target)
        print("  ↑ %s (%.1fMB) → %s" % (name, os.path.getsize(p) / 1e6, fid))
        n += 1
    print("✓ הועלו %d קבצים ל-https://drive.google.com/drive/folders/%s" % (n, target))


def pull(folder_id, out, rel=""):
    token = access_token()
    for f in children(token, folder_id):
        if f["mimeType"] == "application/vnd.google-apps.folder":
            pull(f["id"], out, os.path.join(rel, f["name"]))
            continue
        if not f["mimeType"].startswith(MEDIA):
            continue
        d = os.path.join(out, rel)
        os.makedirs(d, exist_ok=True)
        r = requests.get("%s/%s" % (API, f["id"]), params={"alt": "media"}, headers=_h(token),
                         timeout=900, stream=True)
        r.raise_for_status()
        raw = os.path.join("/tmp", f["id"])
        with open(raw, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
        base = os.path.splitext(f["name"])[0]
        if f["mimeType"].startswith(VIDEO):
            dst = os.path.join(d, base + ".mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", "scale=-2:'min(1920,ih)'",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac",
                            "-b:a", "128k", "-movflags", "+faststart", dst], check=True)
            os.remove(raw)
        else:
            dst = os.path.join(d, f["name"])
            os.replace(raw, dst)
        print("  ↓ %s/%s (%.1fMB)" % (rel, f["name"], os.path.getsize(dst) / 1e6))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "push":
        push(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "pull":
        pull(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
