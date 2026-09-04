# -*- coding: utf-8 -*-
"""כתיבת תיאור בעברית לתמונה שהגיעה מהדרייב עם שם קובץ של מצלמה.

שם כמו "20260823_122657.jpg" לא מתאר כלום, ו-alt כזה גרוע מכלום: קורא מסך
מקריא את המספר בקול, וגוגל רואה רעש. כאן שולחים את התמונה עצמה ל-Claude
ומקבלים תיאור קצר בעברית — בדיוק מה שאדם היה כותב.

דורש ANTHROPIC_API_KEY (סוד ב-GitHub, או שורה ב-.env להרצה מקומית). בלי מפתח
או בלי החבילה — מחזירים מחרוזת ריקה, והעמוד נופל לטקסט ברירת המחדל שלו.
העלות היא בערך חצי סנט לתמונה, ורק על תמונות עם שם גנרי.
"""

import base64
import io
import os

from PIL import Image, ImageOps

MODEL = "claude-opus-5"
MAX_EDGE = 800          # מספיק כדי לזהות סוג פירסינג, וחוסך טוקנים
MAX_ALT_CHARS = 80

# תקרה קשיחה לריצה אחת. באג או לולאה לא יכולים לגלוש מעבר לזה — מה שמעל
# פשוט עולה בלי תיאור ומסומן ב-PR. אפשר לשנות במשתנה הסביבה NAME_IMAGES_MAX.
MAX_PER_RUN = int(os.environ.get("NAME_IMAGES_MAX", "40"))
COST_PER_IMAGE = 0.005  # דולר, הערכה גסה לתמונה מוקטנת + תשובה קצרה

SYSTEM = """אתה כותב טקסט חלופי (alt) בעברית לתמונות באתר של קליניקת קעקועים
ופירסינג בשם "פרדו אינק ארט".

כללים:
- משפט אחד קצר, 3 עד 8 מילים, בלי נקודה בסוף.
- לתאר מה רואים: סוג הפירסינג או הקעקוע ואיפור/מיקום בגוף. למשל
  "פירסינג הליקס באוזן עם עגיל כסף" או "קעקוע ורד על הכתף".
- אם יש כיתוב בתוך התמונה שמסביר מה בוצע — להסתמך עליו.
- לא להמציא פרטים שלא רואים, לא לנחש שמות, גיל או מגדר של אנשים, ולא לתאר
  את פניהם.
- לענות בטקסט התיאור בלבד, בלי מרכאות ובלי הקדמה."""

PROMPT = {
    "piercing": "תמונה מגלריית הפירסינג. כתוב טקסט חלופי.",
    "tattoo": "תמונה מגלריית הקעקועים. כתוב טקסט חלופי.",
    "laser": "תמונה מגלריית הסרת קעקועים בלייזר. כתוב טקסט חלופי.",
}

_client = None
_unavailable = None
_calls = 0


def _get_client():
    """לקוח יחיד לכל הריצה, או None אם אי אפשר — בלי להפיל את הסנכרון."""
    global _client, _unavailable
    if _client or _unavailable:
        return _client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        _unavailable = "אין ANTHROPIC_API_KEY — תמונות עם שם גנרי יעלו בלי תיאור"
        print(_unavailable)
        return None
    try:
        import anthropic
    except ImportError:
        _unavailable = "החבילה anthropic לא מותקנת — תמונות עם שם גנרי יעלו בלי תיאור"
        print(_unavailable)
        return None
    _client = anthropic.Anthropic()
    return _client


def _payload(raw):
    """מקטין את התמונה ומחזיר אותה כ-base64 — פחות טוקנים, אותו זיהוי."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def describe(raw, category):
    """תיאור בעברית לתמונה, או מחרוזת ריקה אם לא הסתדר."""
    global _calls
    client = _get_client()
    if client is None:
        return ""
    if _calls >= MAX_PER_RUN:
        if _calls == MAX_PER_RUN:
            print("הגעתי לתקרה של %d תיאורים בריצה — השאר יעלו בלי תיאור"
                  % MAX_PER_RUN)
            _calls += 1
        return ""
    _calls += 1
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=SYSTEM,
            output_config={"effort": "low"},   # משימה פשוטה, אין צורך בחשיבה עמוקה
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": "image/jpeg",
                                "data": _payload(raw)}},
                    {"type": "text",
                     "text": PROMPT.get(category, PROMPT["piercing"])},
                ],
            }],
        )
    except Exception as exc:   # תקלת רשת או מכסה לא תפיל את הסנכרון
        print("כתיבת התיאור נכשלה: %s" % str(exc)[:200])
        return ""

    if getattr(response, "stop_reason", None) == "refusal":
        return ""
    text = " ".join(b.text for b in response.content if b.type == "text").strip()
    text = text.strip('"“”').replace("\n", " ").strip()
    return text[:MAX_ALT_CHARS]


def spent():
    """שורת סיכום לסוף הריצה — כמה קריאות היו וכמה זה עלה בערך."""
    used = min(_calls, MAX_PER_RUN)
    if not used:
        return "לא נשלחה אף תמונה לכתיבת תיאור"
    return "נשלחו %d תמונות לכתיבת תיאור (עלות משוערת: %.2f דולר)" % (
        used, used * COST_PER_IMAGE)
