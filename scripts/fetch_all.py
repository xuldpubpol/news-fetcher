import json, os, time, sys
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = {
  "foreign-affairs": {"name": "Foreign Affairs", "url": "https://www.foreignaffairs.com/rss.xml"},
  "bbc": {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
  "the-diplomat": {"name": "The Diplomat", "url": "https://thediplomat.com/feed/"},
}

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(REPO_ROOT, "news-data")

def fetch_source(key):
  cfg = SOURCES.get(key, {})
  hdrs = {"User-Agent": "Mozilla/5.0"}
  try:
    req = urllib.request.Request(cfg["url"], headers=hdrs)
    resp = urllib.request.urlopen(req, timeout=30)
    root = ET.fromstring(resp.read())
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for e in root.iter():
      t = e.tag.split("}")[-1]
      if t in ("item", "entry"): items.append(e)
    res = []
    for e in items[:50]:
      def gt(t):
        for s in e.iter():
          st = s.tag.split("}")[-1]
          if st == t and s.text: return s.text.strip()
        return ""
      t = gt("title")
      if not t: continue
      lnk = ""
      for s in e.iter():
        st = s.tag.split("}")[-1]
        if st == "link": lnk = s.get("href", "") or (s.text or "")
      if not lnk: lnk = gt("guid")
      res.append({"source":key,"title":t,"link":lnk,"full_text":"",
        "summary":(gt("description") or gt("summary") or "")[:500],
        "author":(gt("author") or gt("dc:creator") or ""),
        "published":(gt("pubDate") or gt("published") or ""),
        "fetched_at":now})
    return res
  except Exception as e: print("Err:", key, e); return []

def main():
  all_a = {}
  for k in SOURCES:
    print("Fetching", SOURCES[k]["name"])
    arts = fetch_source(k)
    if arts:
      os.makedirs(DATA_DIR, exist_ok=True)
      fp = os.path.join(DATA_DIR, k+".json")
      with open(fp, "w", encoding="utf-8") as f:
        json.dump({"source":k,"fetched_at":datetime.now(timezone.utc).isoformat(),
          "count":len(arts),"articles":arts}, f, ensure_ascii=False, indent=2)
      print("  Saved", len(arts))
      all_a[k] = arts
    time.sleep(2)
  if all_a:
    idx = {"fetched_at":datetime.now(timezone.utc).isoformat(),"sources":{}}
    for k,arts in all_a.items():
      idx["sources"][k] = {"name":SOURCES[k]["name"],"count":len(arts)}
    with open(os.path.join(DATA_DIR, "index.json"), "w", encoding="utf-8") as f:
      json.dump(idx, f, ensure_ascii=False, indent=2)
    print("Done:", sum(len(a) for a in all_a.values()))

if __name__ == "__main__":
  main()