import os
import json
import feedparser
import urllib.request
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 擴充後的 RSS 來源
RSS_FEEDS = [
    # 國外科技媒體
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.technologyreview.com/feed/",
    "https://feeds.feedburner.com/VentureBeat",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://www.artificialintelligence-news.com/feed/",
    
    # 開發者與論文社群
    "https://news.ycombinator.com/rss",
    "https://paperswithcode.com/rss/latest",
    "https://rss.arxiv.org/rss/cs.AI",
    "https://huggingface.co/blog/feed.xml",
    
    # 精選電子報
    "https://tldr.tech/ai/rss",
    "https://bensbites.beehiiv.com/feed",
    
    # 國內科技媒體
    "https://www.ithome.com.tw/rss",
    "https://www.inside.com.tw/feed",
    "https://technews.tw/feed/",
    "https://buzzorange.com/techorange/feed/"
]

def call_gemini_api(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(text_content)

def send_line_message(articles):
    """將新聞摘要通過 LINE Messaging API Push 訊息發送給使用者"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ 未設定 LINE Token 或 User ID，跳過 LINE 通報。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    message_text = f"🤖 AI Daily Digest ({today})\n"
    message_text += "====================\n\n"
    
    # 取前 5 篇重點新聞
    for idx, item in enumerate(articles[:5], 1):
        message_text += f"{idx}. {item.get('title')}\n"
        for point in item.get('summary', []):
            message_text += f" • {point}\n"
        message_text += f"🔗 原文：{item.get('url')}\n\n"

    message_text += "更多完整新聞請見 GitHub Pages 網站！"

    url = "https://api.line.me/v2/bot/message/push"
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as resp:
            print("📱 LINE 訊息通報發送成功！")
    except Exception as e:
        print(f"❌ LINE 通報發送失敗: {e}")

def fetch_and_summarize():
    articles = []
    print("開始抓取 RSS...")
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:1]:
                prompt = f"""
                請分析以下文章並提供繁體中文摘要：
                標題：{entry.title}
                內容：{entry.get('summary', entry.get('title', ''))}
                
                輸出 JSON：
                {{
                    "title": "繁體中文標題",
                    "summary": ["重點1", "重點2", "重點3"],
                    "url": "{entry.link}"
                }}
                """
                try:
                    summary_json = call_gemini_api(prompt)
                    articles.append(summary_json)
                except Exception as api_err:
                    print(f"API 失敗: {api_err}")
        except Exception as feed_err:
            print(f"RSS 失敗: {feed_err}")

    # 儲存 JSON
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = "src/assets/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{today}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # 發送 LINE 訊息
    send_line_message(articles)

if __name__ == "__main__":
    fetch_and_summarize()
