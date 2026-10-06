import os
import json
import time
import urllib.request
import urllib.error

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def _send_groq_request(prompt: str, response_format_type: str = "json_object", retries: int = 3):
    """底層共用的 Groq API 請求函式"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise Exception("❌ 未偵測到 GROQ_API_KEY 環境變數")

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    # 🟢 固定使用確定可執行的 qwen 模型
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": "你是一個專業編輯，請嚴格只輸出合法的 JSON 格式內容。"},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": response_format_type},
        "temperature": 0.2
    }

    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'User-Agent': USER_AGENT
    }
    req = urllib.request.Request(url, data=data, headers=headers)

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return json.loads(result['choices'][0]['message']['content'])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (attempt + 1) * 15
                print(f"⏳ Groq 限流 (429)，等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
            else:
                print(f"❌ Groq API 錯誤 ({e.code}): {e.read().decode('utf-8')}")
                if attempt == retries - 1:
                    raise e
                time.sleep(3)
    return None

def summarize_news_batch(articles_chunk) -> list:
    """批次將多篇新聞一次發送給 API 處理"""
    prompt = "請分析以下多篇新聞，並分別提供繁體中文標題與 2~3 點摘要。\n\n"
    for idx, item in enumerate(articles_chunk, 1):
        prompt += f"--- 新聞 {idx} ---\n標題：{item['raw_title']}\n內容：{item['raw_summary'][:800]}\n鏈結：{item['url']}\n\n"

    prompt += """
請嚴格輸出合法 JSON 格式，結構如下：
{
  "articles": [
    {
      "title": "繁體中文標題",
      "summary": ["重點1", "重點2", "重點3"],
      "url": "原文鏈結"
    }
  ]
}
"""
    result = _send_groq_request(prompt, retries=5)
    return result.get("articles", []) if result else []

def summarize_stock_news(title: str) -> str:
    """針對單筆財經新聞進行摘要"""
    prompt = f"""
    請針對以下財經新聞提供繁體中文摘要重點：
    新聞標題：{title}

    請輸出 JSON：
    {{
        "summary": "一句話總結重點"
    }}
    """
    res = _send_groq_request(prompt)
    return res.get("summary", "無摘要") if res else title

def parse_credit_card_statement(raw_text: str) -> list:
    """將信用卡對帳單的原始文字解析為結構化 JSON"""
    prompt = f"""
    請幫我分析以下信用卡對帳單的原始文字。
    你需要精準提取出每一筆「消費紀錄」，並忽略繳款紀錄、紅利點數、循環利息等無關資訊。
    
    請注意：金額請轉換為純數字。日期請統一轉換為 YYYY-MM-DD 格式（假設年份為今年）。

    請嚴格輸出 JSON 格式如下：
    {{
      "transactions": [
        {{"date": "2026-10-05", "merchant": "全聯福利中心", "amount": 500}},
        {{"date": "2026-10-06", "merchant": "台灣高鐵", "amount": 1200}}
      ]
    }}

    原始對帳單文字：
    {raw_text}
    """
    
    # 呼叫你原本寫好的 _send_groq_request
    res = _send_groq_request(prompt)
    
    # 如果有成功解析，就回傳 transactions 陣列；否則回傳空陣列
    return res.get("transactions", []) if res else []