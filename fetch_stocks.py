import time
import feedparser
import urllib.parse
import yfinance as yf
from datetime import datetime

# 從共用技能庫載入模組
from skills.ai_summarizer import summarize_stock_news
from skills.notifier import send_line_text

TARGET_STOCKS = [
    {"symbol": "2330.TW", "name": "台積電"},
    {"symbol": "2317.TW", "name": "鴻海"},
    {"symbol": "NVDA", "name": "NVIDIA"}
]

def get_stock_data(symbol):
    """呼叫 yfinance 抓取即時股價"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        last_price = round(info.last_price, 2)
        prev_close = round(info.previous_close, 2)
        change = round(last_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2)
        
        sign = "+" if change > 0 else ""
        return {"price": last_price, "change_str": f"{sign}{change} ({sign}{change_pct}%)"}
    except Exception as e:
        print(f"❌ 取得 {symbol} 股價失敗: {e}")
        return {"price": "N/A", "change_str": "N/A"}

def fetch_stock_news(query_name):
    """抓取並摘要單一股票新聞"""
    encoded_query = urllib.parse.quote(query_name)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link
        
        # 呼叫技能進行摘要
        summary = summarize_stock_news(title)
        news_items.append({"title": title, "summary": summary, "url": link})
        time.sleep(2)
        
    return news_items

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
    
    # 組合文字訊息
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
        
    # 呼叫通知技能發送
    send_line_text(message_text)

if __name__ == "__main__":
    main()