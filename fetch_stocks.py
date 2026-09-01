import os
import json
import time
import feedparser
import urllib.request
import urllib.error
import yfinance as yf
from datetime import datetime

# 1. 環境變數
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 2. 設定你要追蹤的股票清單 (台股請加 .TW 或 .TWO，美股直接填代碼)
TARGET_STOCKS = [
    {"symbol": "2330.TW", "name": "台積電"},
    {"symbol": "2317.TW", "name": "鴻海"},
    {"symbol": "NVDA", "name": "NVIDIA"}
]

def call_groq_api(prompt, retries=3):
    if not GROQ_API_KEY:
        raise Exception("❌ 未偵測到 GROQ_API_KEY")

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "groq/compound-mini",
        "messages": [
            {"role": "system", "content": "你是一個專業的財經編輯，請嚴格只輸出合法的 JSON 格式內容。"},
            {"role": "user", "content": prompt}
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
                return json.loads(result['choices'][0]['message']['content'])
        except urllib.error.HTTPError as e:
            time.sleep(3)
    return None

def get_stock_data(symbol):
    """抓取即時股價與漲跌幅"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        last_price = round(info.last_price, 2)
        prev_close = round(info.previous_close, 2)
        change = round(last_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2)
        
        sign = "+" if change > 0 else ""
        return {
            "price": last_price,
            "change_str": f"{sign}{change} ({sign}{change_pct}%)"
        }
    except Exception as e:
        print(f"❌ 取得 {symbol} 股價失敗: {e}")
        return {"price": "N/A", "change_str": "N/A"}

def fetch_stock_news(query_name):
    """從 Google News RSS 抓取特定股票最新新聞"""
    encoded_query = urllib.parse.quote(query_name)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries[:2]: # 每檔股票取前 2 條新聞
        title = entry.title
        link = entry.link
        
        prompt = f"""
        請針對以下財經新聞提供繁體中文摘要重點：
        新聞標題：{title}

        請輸出 JSON：
        {{
            "summary": "一句話總結重點"
        }}
        """
        res = call_groq_api(prompt)
        summary = res.get("summary", "無摘要") if res else title
        news_items.append({"title": title, "summary": summary, "url": link})
        time.sleep(2)
        
    return news_items

def send_stock_line_message(report_data):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ 未設定 LINE 憑證，跳過發送。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    message_text = f"📈 每日個股動態與焦點新聞 ({today})\n====================\n\n"

    for stock in report_data:
        message_text += f"🔹 {stock['name']} ({stock['symbol']})\n"
        message_text += f"   股價：{stock['price']} | 漲跌：{stock['change_str']}\n"
        message_text += "   重點新聞：\n"
        for idx, news in enumerate(stock['news'], 1):
            message_text += f"   {idx}. {news['summary']}\n"
            message_text += f"      🔗 {news['url']}\n"
        message_text += "\n"

    url = "https://api.line.me/v2/bot/message/push"
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    
    try:
        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as resp:
            print("📱 股票追蹤 LINE 訊息發送成功！")
    except Exception as e:
        print(f"❌ LINE 發送失敗: {e}")

def main():
    report_data = []
    print("開始抓取股票與新聞資料...")
    
    for stock in TARGET_STOCKS:
        print(f"抓取 {stock['name']}...")
        stock_info = get_stock_data(stock['symbol'])
        news_list = fetch_stock_news(stock['name'])
        
        report_data.append({
            "name": stock['name'],
            "symbol": stock['symbol'],
            "price": stock_info['price'],
            "change_str": stock_info['change_str'],
            "news": news_list
        })
    
    send_stock_line_message(report_data)

if __name__ == "__main__":
    main()
