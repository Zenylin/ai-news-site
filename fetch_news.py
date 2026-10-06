import os
import json
import re
import time
import feedparser
from datetime import datetime

# 從共用技能庫載入模組
from skills.ai_summarizer import summarize_news_batch
from skills.notifier import send_news_flex_message

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.ithome.com.tw/rss",
    "https://www.inside.com.tw/feed",
    # ... 其他你想保留的網址
]

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return text.replace('"', "'").replace('\n', ' ').replace('\r', '').strip()

def fetch_and_summarize():
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = "src/assets/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{today}.json")

    # 1. 快取檢查
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
            if articles:
                print(f"📁 發現今日 ({today}) 已有抓取紀錄，直接發送 LINE 推播...")
                send_news_flex_message(articles)
                return
        except Exception:
            pass

    # 2. 抓取 RSS
    raw_articles = []
    print("開始抓取 RSS 原文...")
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url, request_headers={'User-Agent': USER_AGENT})
            for entry in feed.entries[:2]:
                raw_articles.append({
                    "raw_title": clean_text(entry.title),
                    "raw_summary": clean_text(entry.get('summary', entry.get('title', ''))),
                    "url": entry.link
                })
        except Exception as feed_err:
            print(f"RSS 失敗 [{feed_url}]: {feed_err}")

    # 3. 呼叫技能進行分析
    processed_articles = []
    chunk_size = 5
    for i in range(0, len(raw_articles), chunk_size):
        chunk = raw_articles[i:i + chunk_size]
        print(f"🚀 正在批次分析第 {i+1} ~ {i+len(chunk)} 篇新聞...")
        try:
            res_list = summarize_news_batch(chunk)
            processed_articles.extend(res_list)
            time.sleep(10) # 避免 API 限流
        except Exception as err:
            print(f"❌ 批次處理失敗: {err}")

    # 4. 儲存與發送
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

    if processed_articles:
        send_news_flex_message(processed_articles)

if __name__ == "__main__":
    fetch_and_summarize()