#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""הפקת refresh token לגישה לגוגל דרייב — הרצה חד-פעמית במחשב.

ההרשאה היא על כל הדרייב, כי הסקריפטים גם מעבירים תמונות שפורסמו לתיקיית
"פורסם" וגם שולחים לפח את מה שכבר ירד למחשב.

מריצים:  python tools/gdrive_auth.py <CLIENT_ID> <CLIENT_SECRET>

נפתח דפדפן, מאשרים גישה לחשבון kohpmu@gmail.com, והסקריפט מדפיס את הטוקן.
את הטוקן מדביקים ב-GitHub → Settings → Secrets and variables → Actions
כ-GDRIVE_REFRESH_TOKEN (וגם GDRIVE_CLIENT_ID / GDRIVE_CLIENT_SECRET).

הטוקן אינו נשמר לקובץ בכוונה — הוא מודפס למסך בלבד.
"""

import http.server
import os
import secrets
import sys
import urllib.parse
import webbrowser

import requests

SCOPE = "https://www.googleapis.com/auth/drive"
PORT = 8080
REDIRECT_URI = "http://localhost:%d/" % PORT

_result = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _result.update({k: v[0] for k, v in query.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = "code" in _result
        self.wfile.write(("<html dir='rtl'><body style='font-family:sans-serif;"
                          "text-align:center;padding-top:60px'><h2>%s</h2>"
                          "<p>אפשר לסגור את החלון ולחזור לטרמינל.</p></body></html>"
                          % ("הגישה אושרה ✅" if ok else "האישור בוטל ❌")
                          ).encode("utf-8"))

    def log_message(self, *args):
        pass


def save_env(client_id, client_secret, token):
    """כותב את שלושת הערכים ל-.env בשורש הריפו, בלי להדפיס את הטוקן למסך."""
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    values = {
        "GDRIVE_CLIENT_ID": client_id,
        "GDRIVE_CLIENT_SECRET": client_secret,
        "GDRIVE_REFRESH_TOKEN": token,
    }
    kept = []
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as fh:
            kept = [ln.rstrip("\n") for ln in fh
                    if ln.split("=", 1)[0].strip() not in values]
    with open(env_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept + ["%s=%s" % kv for kv in values.items()]) + "\n")


def main():
    if len(sys.argv) == 3:
        client_id, client_secret = sys.argv[1], sys.argv[2]
    else:  # אחרת מהסביבה, כדי לא להדביק סודות בשורת הפקודה
        client_id = os.environ.get("GDRIVE_CLIENT_ID") or os.environ.get("GBP_CLIENT_ID")
        client_secret = (os.environ.get("GDRIVE_CLIENT_SECRET")
                         or os.environ.get("GBP_CLIENT_SECRET"))
    if not client_id or not client_secret:
        sys.exit("שימוש: python tools/gdrive_auth.py <CLIENT_ID> <CLIENT_SECRET>\n"
                 "או הגדרת GDRIVE_CLIENT_ID / GDRIVE_CLIENT_SECRET בסביבה.")
    state = secrets.token_urlsafe(16)

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })

    server = http.server.HTTPServer(("localhost", PORT), Handler)

    print("נפתח דפדפן לאישור הגישה. אם לא — פתחי ידנית:\n%s\n" % auth_url)
    webbrowser.open(auth_url)
    server.handle_request()  # חוזר אחרי שגוגל מפנה חזרה ל-localhost

    if _result.get("state") != state:
        sys.exit("ה-state שחזר לא תואם — מבטלים מחשש לזיוף בקשה.")
    if "code" not in _result:
        sys.exit("לא התקבל אישור: %s" % _result.get("error"))

    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": _result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=30)
    if not r.ok:
        sys.exit("החלפת הקוד בטוקן נכשלה: %s %s" % (r.status_code, r.text[:400]))

    token = r.json().get("refresh_token")
    if not token:
        sys.exit("גוגל לא החזירה refresh token. הסירי את ההרשאה בכתובת "
                 "https://myaccount.google.com/permissions ונסי שוב.")

    save_env(client_id, client_secret, token)
    print("\nהטוקן נשמר ב-.env בשורש הריפו (לא נכנס לגיט ולא מודפס למסך).")
    print("להעלאה ל-GitHub:  gh secret set GDRIVE_REFRESH_TOKEN < ...  — או מהתיעוד ב-README")


if __name__ == "__main__":
    main()
