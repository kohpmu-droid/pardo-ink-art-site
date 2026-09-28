# -*- coding: utf-8 -*-
"""Rebuild sitemap.xml from every .html page in the repo root.

Runs after every publish run (see publish_from_queue.py), so articles published
from the queue, by hand or by any other flow all reach the sitemap within one run.
The URL of each page is taken from its canonical link."""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://pardoinkart.com/"
CANON = re.compile(r'<link rel="canonical" href="([^"]+)"')


def build():
    urls = []
    for p in sorted(ROOT.glob("*.html")):
        m = CANON.search(p.read_text(encoding="utf-8"))
        url = m.group(1) if m else BASE + p.name
        if p.name == "index.html":
            urls.insert(0, url)
        else:
            urls.append(url)
    body = "".join("  <url><loc>%s</loc></url>\n" % u for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + body + "</urlset>\n")
    path = ROOT / "sitemap.xml"
    if not path.exists() or path.read_text(encoding="utf-8") != xml:
        path.write_text(xml, encoding="utf-8")
    return len(urls)


if __name__ == "__main__":
    print("sitemap: %d pages" % build())
