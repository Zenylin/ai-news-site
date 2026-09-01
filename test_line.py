import os
import json
import urllib.request

# 請填入你的 LINE 憑證進行測試
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "你的_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "你的_USER_ID")

def test_push_message():
    url = "https://api.line.me/v2/bot/message/push"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": "🧪 測試訊息：LINE Bot 連結成功！\n每日 AI 新聞自動通報功能運作正常。"
            }
        ]
    }
    
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ 發送成功！HTTP Status: {response.status}")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

if __name__ == "__main__":
    test_push_message()
