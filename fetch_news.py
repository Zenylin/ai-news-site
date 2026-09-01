import os
import json
import re
import time
import feedparser
import urllib.request
import urllib.error
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def get_current_api_key():
    global current_key_index
    if not keys_list:
        return None
    return keys_list[current_key_index % len(keys_list)]

def switch_to_next_key():
    global current_key_index
    if len(keys_list) > 1:
        current_key_index = (current_key_index + 1) % len(keys_list)
        print(f"🔄 已自動切換至第 {current_key_index + 1} 組 Gemini API Key")

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

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return text.replace('"', "'").replace('\n', ' ').replace('\r', '').strip()

def call_groq_api(prompt, retries=5):
    if not GROQ_API_KEY:
        raise Exception("❌ 未偵測到 GROQ_API_KEY 環境變數")

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "groq/compound-mini",
        "messages": [
            {
                "role": "system",
                "content": "你是一個專業的科技新聞編輯，請嚴格只輸出合法的 JSON 格式內容，不要加上任何 Markdown 註解。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }

    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'User-Agent': USER_AGENT
    }
    req = urllib.request.Request(url, data=data, headers=headers)

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['choices'][0]['message']['content']
                return json.loads(content)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            if e.code == 429:
                # 增加退避等待時間（每次增加 8 秒，避免連續碰撞限流）
                wait_time = (attempt + 1) * 8
                print(f"⏳ Groq 限流 (429)，等待 {wait_time} 秒後重試 (第 {attempt+1}/{retries} 次)...")
                time.sleep(wait_time)
            else:
                print(f"❌ Groq API 錯誤 ({e.code}): {error_body}")
                raise e
    raise Exception("❌ 已達到 Groq API 最大重試次數")

def send_line_message(articles):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ 未設定 LINE Token 或 User ID，跳過 LINE 通報。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    
    # 限制最多推播 10 篇卡片（LINE Flex Carousel 單次上限 10 頁）
    bubbles = []
    for idx, item in enumerate(articles[:10], 1):
        title = item.get("title", "無標題")
        url = item.get("url", "#")
        summaries = item.get("summary", [])

        # 將摘要陣列轉為 Text Component
        summary_components = []
        for point in summaries[:3]: # 每張卡片最多放 3 點摘要
            summary_components.append({
                "type": "text",
                "text": f"• {point}",
                "size": "xs",
                "color": "#666666",
                "wrap": True,
                "margin": "xs"
            })

        # 單張卡片 Structure (Bubble)
        bubble = {
            "type": "bubble",
            "size": "micro", # 迷你卡片橫滑體驗最佳
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1DB446",
                "contents": [
                    {
                        "type": "text",
                        "text": f"NO. {idx}",
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "size": "xs"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "sm",
                        "wrap": True,
                        "maxLines": 2
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "contents": summary_components
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1DB446",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "閱讀原文",
                            "uri": url
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    # 組合 Carousel 包裝
    flex_payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "flex",
                "altText": f"🤖 AI Daily Digest ({today}) 新聞卡片推送",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }
        ]
    }

    url = "https://api.line.me/v2/bot/message/push"
    try:
        data = json.dumps(flex_payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as resp:
            print(f"📱 LINE Flex Message 卡片推播發送成功！（共 {len(bubbles)} 頁卡片）")
    except Exception as e:
        print(f"❌ LINE Flex Message 發送失敗: {e}")

def fetch_and_summarize():
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = "src/assets/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{today}.json")

    # 檢查今日快取
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
            if articles:
                print(f"📁 發現今日 ({today}) 已有抓取紀錄 ({len(articles)} 篇)，跳過 API 分析，直接發送 LINE 推播...")
                send_line_message(articles)
                return
        except Exception as read_err:
            print(f"⚠️ 讀取快取失敗 ({read_err})，重新執行抓取流程...")

    articles = []
    print("開始抓取 RSS...")
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url, request_headers={'User-Agent': USER_AGENT})
            for entry in feed.entries[:2]:
                title = clean_text(entry.title)
                raw_summary = clean_text(entry.get('summary', entry.get('title', '')))

                prompt = f"""
                請分析以下文章並提供繁體中文摘要：
                標題：{title}
                內容：{raw_summary[:2000]}

                請輸出合法 JSON 格式，結構如下：
                {{
                    "title": "繁體中文標題",
                    "summary": ["重點1", "重點2", "重點3"],
                    "url": "{entry.link}"
                }}
                """
                try:
                    summary_json = call_groq_api(prompt)
                    articles.append(summary_json)
                    print(f"✅ 成功處理: {title}")
                    time.sleep(3)
                except Exception as api_err:
                    print(f"API 失敗 [{title}]: {api_err}")
        except Exception as feed_err:
            print(f"RSS 失敗 [{feed_url}]: {feed_err}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    if articles:
        send_line_message(articles)

if __name__ == "__main__":
    fetch_and_summarize()
