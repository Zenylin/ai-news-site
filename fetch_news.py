import os
import json
import re
import time
import feedparser
import urllib.request
import urllib.error
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
#LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
#LINE_USER_ID = os.environ.get("LINE_USER_ID")
# groq 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

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

def call_groq_api(prompt, retries=3):
    if not GROQ_API_KEY:
        raise Exception("❌ 未偵測到 GROQ_API_KEY 環境變數")

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        # 修正：精確模型代號
        "model": "groq/compound-mini",
        "messages": [
            {
                "role": "system",
                "content": "你是一個專業的科技新聞編輯，請嚴格只輸出合法的 JSON 格式內容，不要加上任何 Markdown 註解（如 ```json）。"
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
        # 關鍵修復：加入 User-Agent 避免觸發 Cloudflare 1010 防火牆阻擋
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
                print(f"⏳ Groq 限流 (429)，等待 5 秒後重試 (第 {attempt+1}/{retries} 次)...")
                time.sleep(5)
            else:
                print(f"❌ Groq API 錯誤 ({e.code}): {error_body}")
                raise e
    raise Exception("❌ 已達到 Groq API 最大重試次數")


def send_line_message(articles):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ 未設定 LINE Token 或 User ID，跳過 LINE 通報。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    message_text = f"🤖 AI Daily Digest ({today})\n====================\n\n"

    for idx, item in enumerate(articles[:5], 1):
        message_text += f"{idx}. {item.get('title')}\n"
        for point in item.get('summary', []):
            message_text += f" • {point}\n"
        message_text += f"🔗 原文：{item.get('url')}\n\n"

    url = "[https://api.line.me/v2/bot/message/push](https://api.line.me/v2/bot/message/push)"
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}

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
            feed = feedparser.parse(feed_url, request_headers={'User-Agent': USER_AGENT})
            for entry in feed.entries[:1]:
                title = clean_text(entry.title)
                raw_summary = clean_text(entry.get('summary', entry.get('title', '')))

                prompt = f"""
                請分析以下文章並提供繁體中文摘要：
                標題：{title}
                內容：{raw_summary[:1000]}

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
                    time.sleep(1) # Groq 速度極快，只需短暫停頓
                except Exception as api_err:
                    print(f"API 失敗 [{title}]: {api_err}")
        except Exception as feed_err:
            print(f"RSS 失敗 [{feed_url}]: {feed_err}")

    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = "src/assets/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{today}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    if articles:
        send_line_message(articles)

if __name__ == "__main__":
    fetch_and_summarize()
