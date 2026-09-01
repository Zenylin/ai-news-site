import os
import json
import feedparser
import urllib.request
import urllib.parse
from datetime import datetime

# 從環境變數讀取 API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 精選 10 個穩定且完全可用的 RSS 來源
RSS_FEEDS = [
    # 國外主流與技術媒體
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://feeds.feedburner.com/VentureBeat",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.artificialintelligence-news.com/feed/",
    
    # 開發者社群與論文
    "https://news.ycombinator.com/rss",
    "https://rss.arxiv.org/rss/cs.AI",
    "https://huggingface.co/blog/feed.xml",
    
    # 國內華語科技媒體
    "https://www.ithome.com.tw/rss",
    "https://technews.tw/feed/",
    "https://www.inside.com.tw/feed"
]

def call_gemini_api(prompt):
    """發送 HTTP 請求給 Gemini REST API"""
    # 將 gemini-1.5-flash 修正為 gemini-2.5-flash
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


def fetch_and_summarize():
    articles = []
    print("開始抓取各大 RSS 新聞源...")
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
                
            # 每個來源取最新 1 篇
            entry = feed.entries[0]
            summary_text = getattr(entry, 'summary', getattr(entry, 'title', ''))
            
            prompt = f"""
            請分析以下新聞並提供繁體中文摘要：
            標題：{entry.title}
            內容：{summary_text}
            
            請嚴格輸出 JSON 格式：
            {{
                "title": "繁體中文翻譯標題",
                "summary": ["重點1", "重点2", "重點3"],
                "url": "{entry.link}"
            }}
            """
            
            try:
                summary_json = call_gemini_api(prompt)
                articles.append(summary_json)
                print(f"✅ 成功處理: {entry.title}")
            except Exception as api_err:
                print(f"⚠️ API 處理失敗 [{entry.title}]: {api_err}")
                
        except Exception as feed_err:
            print(f"❌ RSS 抓取失敗 [{feed_url}]: {feed_err}")

    # 寫入 JSON 檔
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = "src/assets/data"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{today}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 完成！成功儲存 {len(articles)} 篇摘要檔案至: {output_file}")

if __name__ == "__main__":
    fetch_and_summarize()
