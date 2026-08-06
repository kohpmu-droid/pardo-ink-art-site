# -*- coding: utf-8 -*-
"""Refresh the YouTube section of blog.html from the channel's public RSS feed.
Runs in GitHub Actions (no credentials needed). Idempotent."""
import re, sys, html, urllib.request, pathlib

CHANNEL_ID = "UC3aPahvGhEkosbIr8hBCcyg"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID
BLOG = pathlib.Path(__file__).resolve().parent.parent / "blog.html"
N = 6
START, END = "<!-- YT:START -->", "<!-- YT:END -->"

def fetch_feed():
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def parse(xml):
    vids = []
    for entry in re.findall(r"<entry>.*?</entry>", xml, re.S):
        vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", entry)
        title = re.search(r"<title>([^<]*)</title>", entry)
        if vid and title:
            vids.append((vid.group(1).strip(), html.unescape(title.group(1).strip())))
    return vids[:N]

def card(video_id, title):
    safe = html.escape(title)
    short = html.escape(title[:70])
    return (
        '                <div class="card rounded-2xl overflow-hidden">\n'
        '                    <div class="relative w-full bg-black" style="aspect-ratio:9/16;">\n'
        '                        <iframe class="absolute inset-0 w-full h-full" src="https://www.youtube.com/embed/%s" title="%s" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen loading="lazy"></iframe>\n'
        '                    </div>\n'
        '                    <div class="p-5 text-right">\n'
        '                        <h3 class="text-base font-bold accent-wine mb-2 leading-snug">%s</h3>\n'
        '                        <a href="https://www.youtube.com/watch?v=%s" target="_blank" rel="noopener" class="accent-wine font-semibold text-sm">צפו ביוטיוב ←</a>\n'
        '                    </div>\n'
        '                </div>'
        % (video_id, short, safe, video_id)
    )

def main():
    vids = parse(fetch_feed())
    if not vids:
        print("ERROR: no videos parsed from feed", file=sys.stderr)
        return 1
    block = "\n" + "\n".join(card(v, t) for v, t in vids) + "\n"
    src = BLOG.read_text(encoding="utf-8")
    if START not in src or END not in src:
        print("ERROR: markers not found in blog.html", file=sys.stderr)
        return 1
    new = re.sub(re.escape(START) + r".*?" + re.escape(END),
                 START + block + END, src, count=1, flags=re.S)
    if new == src:
        print("NO CHANGE: latest %d videos already current" % len(vids))
        return 0
    BLOG.write_text(new, encoding="utf-8")
    print("CHANGED: updated blog with latest %d videos" % len(vids))
    return 0

if __name__ == "__main__":
    sys.exit(main())
