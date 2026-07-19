import json, os, time
from datetime import datetime, timezone

SOURCES = {
    'foreign-affairs': {
        'url': 'https://rsshub.app/foreignaffairs',
        'name': 'Foreign Affairs',
        'lang': 'en',
    },
    'economist': {
        'url': 'https://rsshub.app/economist/latest',
        'name': 'The Economist',
        'lang': 'en',
    },
    'bbc': {
        'url': 'https://rsshub.app/bbc/world',
        'name': 'BBC News',
        'lang': 'en',
    },
    'the-diplomat': {
        'url': 'https://rsshub.app/the-diplomat',
        'name': 'The Diplomat',
        'lang': 'en',
    },
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'news-data')
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_rss(url):
    import feedparser
    import requests
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        return feed
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return None

def extract_articles(feed, source_key):
    articles = []
    now = datetime.now(timezone.utc).isoformat()
    for entry in feed.entries[:30]:
        article = {
            'source': source_key,
            'title': entry.get('title', '').strip(),
            'link': entry.get('link', ''),
            'summary': (entry.get('summary') or entry.get('description', '')).strip()[:500],
            'author': entry.get('author', ''),
            'published': entry.get('published', ''),
            'updated': entry.get('updated', ''),
            'fetched_at': now,
        }
        if article['title']:
            articles.append(article)
    return articles

def save_articles(source_key, articles):
    path = os.path.join(DATA_DIR, f'{source_key}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'source': source_key,
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'count': len(articles),
            'articles': articles,
        }, f, ensure_ascii=False, indent=2)
    print(f'Saved {len(articles)} articles to {path}')

def generate_index(all_data):
    index = {
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'sources': {},
    }
    for key, data in all_data.items():
        total = len(data)
        titles = [a['title'] for a in data[:5]]
        index['sources'][key] = {
            'name': SOURCES[key]['name'],
            'count': total,
            'latest': titles[:5],
        }
    path = os.path.join(DATA_DIR, 'index.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f'Index saved')

def main():
    all_data = {}
    for key, config in SOURCES.items():
        print(f'Fetching {config["name"]}...')
        feed = fetch_rss(config['url'])
        if feed is None:
            continue
        articles = extract_articles(feed, key)
        save_articles(key, articles)
        all_data[key] = articles
        time.sleep(2)
    if all_data:
        generate_index(all_data)
    print('Done')

if __name__ == '__main__':
    main()
