#!/usr/bin/env python3
# Zero-dependency RSS news fetcher
import json, os, time, sys
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET

# DATA_DIR: use GITHUB_WORKSPACE or fall back to repo root
REPO_ROOT = os.environ.get('GITHUB_WORKSPACE') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, 'news-data')

def get_text(child, tag):
    for sub in child.iter():
        t = sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag
        if t == tag and sub.text:
            return sub.text.strip()
    return ''

def fetch_articles(source_key, feed_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
    }
    try:
        req = urllib.request.Request(feed_url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=30)
        content = resp.read()
        root = ET.fromstring(content)
        articles = []
        # Try Atom format first
        ns = {'atom': 'http://www.w3.org/2005/Atom',
              'dc': 'http://purl.org/dc/elements/1.1/',
              'content': 'http://purl.org/rss/1.0/modules/content/'}
        entries = root.findall('.//atom:entry', ns) or root.findall('.//item')
        for entry in entries[:50]:
            title = get_text(entry, 'title')
            link = ''
            for l in entry.findall('.//{http://www.w3.org/2005/Atom}link') or entry.findall('.//link'):
                href = l.get('href', '') or (l.text or '')
                if href: link = href
            if not link and entry.find('.//guid') is not None:
                link = (entry.find('.//guid').text or '')
            summary = ''
            for t in ['summary', 'description', 'content:encoded']:
                val = get_text(entry, t)
                if val: summary = val[:500]; break
            author = get_text(entry, 'author') or get_text(entry, 'dc:creator')
            published = get_text(entry, 'pubDate') or get_text(entry, 'published') or get_text(entry, 'dc:date')
            if title:
                articles.append({
                    'source': source_key, 'title': title.strip(),
                    'link': link.strip(), 'summary': summary.strip(),
                    'author': author.strip(), 'published': published.strip(),
                    'full_text': fetch_full_text(link.strip()) if link.strip() else '',
                    'fetched_at': datetime.now(timezone.utc).isoformat(),
                })
        return articles
    except Exception as e:
        print(f'  Error: {e}')
        return []

def save_data(source_key, articles):
    path = os.path.join(DATA_DIR, f'{source_key}.json')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'source': source_key, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                   'count': len(articles), 'articles': articles}, f, ensure_ascii=False, indent=2)
    print(f'Saved {len(articles)} articles to {path}')

def save_index(all_articles):
    index = {'fetched_at': datetime.now(timezone.utc).isoformat(), 'sources': {}}
    for key, arts in all_articles.items():
        index['sources'][key] = {
            'name': SOURCES[key]['name'],
            'count': len(arts),
            'latest': [a['title'][:60] for a in arts[:5]],
        }
    idx_path = os.path.join(DATA_DIR, 'index.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f'Index saved ({len(all_articles)} sources)')

def main():
    all_articles = {}
    for key, cfg in SOURCES.items():
        print(f'Fetching {cfg["name"]}...')
        articles = []
        for url in cfg['urls']:
            articles = fetch_articles(key, url)
            if articles: break
            time.sleep(1)
        if articles:
            save_data(key, articles)
            all_articles[key] = articles
        time.sleep(2)
    if all_articles:
        save_index(all_articles)
    print(f'Done. Fetched {sum(len(a) for a in all_articles.values())} articles total.')

if __name__ == '__main__':
    main()
def fetch_full_text(url):
    hdrs = {"User-Agent": "Mozilla/5.0 (Win64)"}
    try:
        req = urllib.request.Request(url, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=60)
        html = resp.read().decode("utf-8", errors="replace")
        import re as r2
        p = chr(60) + chr(112) + chr(62) + chr(40) + chr(46) + chr(42) + chr(63) + chr(41) + chr(60) + chr(47) + chr(112) + chr(62)
        parts = r2.findall(p, html)
        txts = [t.strip() for t in parts if len(t.strip()) > 40]
        if txts:
            return chr(10).join(txts[:80])
        return "No article text found"
    except Exception as e:
        return "Error: " + str(e)

