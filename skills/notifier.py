import os
import json
import urllib.request
from datetime import datetime

def _send_line_payload(payload: dict, success_msg: str):
    """底層共用的 LINE API 請求函式"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        print("⚠️ 未設定 LINE Token，跳過推播。")
        return

    url = "https://api.line.me/v2/bot/message/push"
    try:
        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as resp:
            print(success_msg)
    except Exception as e:
        print(f"❌ LINE 發送失敗: {e}")

def send_line_text(message: str):
    """發送純文字 LINE 訊息 (用於股票推播)"""
    user_id = os.environ.get("LINE_USER_ID")
    if not user_id:
        return
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    _send_line_payload(payload, "📱 文字訊息發送成功！")

def send_news_flex_message(articles: list):
    """發送精美的 Flex Message 輪播卡片 (用於新聞推播)"""
    user_id = os.environ.get("LINE_USER_ID")
    if not user_id:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    bubbles = []
    
    for idx, item in enumerate(articles[:10], 1):
        title = item.get("title", "無標題")
        url = item.get("url", "#")
        summaries = item.get("summary", [])

        summary_components = [
            {"type": "text", "text": f"• {point}", "size": "xs", "color": "#666666", "wrap": True, "margin": "xs"} 
            for point in summaries[:3]
        ]

        bubble = {
            "type": "bubble",
            "size": "micro",
            "header": {
                "type": "box", "layout": "vertical", "backgroundColor": "#1DB446",
                "contents": [{"type": "text", "text": f"NO. {idx}", "weight": "bold", "color": "#FFFFFF", "size": "xs"}]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "sm", "wrap": True, "maxLines": 2},
                    {"type": "separator", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "md", "contents": summary_components}
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [{"type": "button", "style": "primary", "color": "#1DB446", "height": "sm", "action": {"type": "uri", "label": "閱讀原文", "uri": url}}]
            }
        }
        bubbles.append(bubble)

    payload = {
        "to": user_id,
        "messages": [{"type": "flex", "altText": f"🤖 AI Daily Digest ({today}) 新聞卡片推送", "contents": {"type": "carousel", "contents": bubbles}}]
    }
    _send_line_payload(payload, f"📱 LINE Flex Message 卡片推播發送成功！（共 {len(bubbles)} 頁卡片）")