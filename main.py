import json
import os
import feedparser

FEED_URL = "https://journals.plos.org/ploscompbiol/feed/atom"
HISTORY_FILE = "history.json"

def load_history():
    """读取历史已处理的文章记录"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def save_history(history):
    """保存更新后的历史记录"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(history), f, ensure_ascii=False, indent=2)

def fetch_new_articles():
    """解析 Atom 源并提取最新未处理条目"""
    history = load_history()
    feed = feedparser.parse(FEED_URL)
    
    new_articles = []
    
    for entry in feed.entries:
        # 使用 entry.id (通常是 DOI/URL) 作为唯一标识
        article_id = getattr(entry, 'id', entry.link)
        
        if article_id not in history:
            # 提取必要字段
            title = entry.title
            link = entry.link
            # PLOS Atom 包含 summary 字段
            summary = getattr(entry, 'summary', '')
            published = getattr(entry, 'published', '')

            new_articles.append({
                "id": article_id,
                "title": title,
                "link": link,
                "summary": summary,
                "published": published
            })
            
            # 记录到历史列表
            history.add(article_id)

    # 保存历史记录
    save_history(history)
    return new_articles

if __name__ == "__main__":
    articles = fetch_new_articles()
    print(f"抓取完成，获取到 {len(articles)} 篇新论文。")
    for a in articles:
        print(f"- {a['title']}")
