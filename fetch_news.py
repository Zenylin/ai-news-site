import os
import json
import re
import time
import feedparser
import urllib.request
import urllib.error
from datetime import datetime

# 1. 支援多種 Key 設定方式：
#    - 方式 A: GEMINI_API_KEYS="Key1,Key2,Key3"
#    - 方式 B: GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3...
raw_keys = os.environ.get("GEMINI_API_KEYS", "")
keys_list = [k.strip() for k in raw_keys.split(",") if k.strip()]

if not keys_list:
    # 搜尋環境變數中所有 GEMINI_API_KEY 開頭的 Key
    for env_name, env_val in os.environ.items():
        if env_name.startswith("GEMINI_API_KEY") and env_val.strip():
            keys_list.append(env_val.strip())

# 全域 Key 索引
current_key_index = 0
#GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
    """清理 HTML 標籤與非法字元，避免破壞 JSON 結構"""
    if not text:
        return ""
    # 去除 HTML 標籤
    text = re.sub(r'<[^>]+>', '', text)
    # 替換雙引號與換行符
    text = text.replace('"', "'").replace('\n', ' ').replace('\r', '')
    return text.strip()

def call_gemini_api(prompt, max_retries=3):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    data = json.dumps(payload).encode('utf-8')
    
    for attempt in range(max_retries):
        api_key = get_current_api_key()
        if not api_key:
            raise Exception("❌ 未偵測到任何有效的 GEMINI_API_KEY 環境變數")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return json.loads(result['candidates'][0]['content']['parts'][0]['text'])
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            # 遇到 429 (Quota Exceeded) 或 400 (Invalid Key)，嘗試輪替 Key
            if e.code in [429, 400] and len(keys_list) > 1:
                print(f"⚠️ API Key 限流或無效 (HTTP {e.code})，嘗試切換 Key... (第 {attempt + 1}/{max_retries} 次)")
                switch_to_next_key()
                time.sleep(2)  # 切換 Key 後稍作等待
            else:
                print(f"❌ Gemini API 錯誤 [{e.code}]: {error_body}")
                raise e

    raise Exception("❌ 所有 Gemini API Keys 皆已達到限額或無效")

def send_line_message(articles):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ 未設定 LINE Token 或 User ID，跳過 LINE 通報。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    message_text = f"🤖 AI Daily Digest ({today})\n"
    message_text += "====================\n\n"
    
    for idx, item in enumerate(articles[:5], 1):
        message_text += f"{idx}. {item.get('title')}\n"
        for point in item.get('summary', []):
            message_text += f" • {point}\n"
        message_text += f"🔗 原文：{item.get('url')}\n\n"

    url = "https://api.line.me/v2/bot/message/push"
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message_text}]
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
                # 清理文字內容
                title = clean_text(entry.title)
                raw_summary = clean_text(entry.get('summary', entry.get('title', '')))
                
                prompt = f"""
                請分析以下文章並提供繁體中文摘要：
                標題：{title}
                內容：{raw_summary[:1000]}

                請嚴格輸出合法 JSON 格式，結構如下：
                {{
                    "title": "繁體中文標題",
                    "summary": ["重點1", "重點2", "重點3"],
                    "url": "{entry.link}"
                }}
                """
                try:
                    summary_json = call_gemini_api(prompt)
                    articles.append(summary_json)
                    print(f"✅ 成功處理: {title}")
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
