import json
import urllib.request
import urllib.error
import time

# 🟢 請在這裡貼上你的 Groq API Key
TEST_API_KEY = "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"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def get_available_models():
    """步驟 1: 取得該金鑰授權的所有模型"""
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {TEST_API_KEY}",
        "User-Agent": USER_AGENT
    }
    
    req = urllib.request.Request(url, headers=headers)
    print("🔄 [步驟 1] 正在向 Groq 查詢你的金鑰授權模型清單...")
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            models = []
            # 過濾掉 whisper (語音) 模型，只保留文字對話模型
            for model in result.get("data", []):
                model_id = model.get("id")
                if "whisper" not in model_id:
                    models.append(model_id)
            return models
    except urllib.error.HTTPError as e:
        print(f"❌ 查詢授權清單失敗 (HTTP {e.code}): {e.read().decode('utf-8')}")
        return []

def test_model_completion(model_name):
    """步驟 2: 實際發送訊息測試模型是否可用"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TEST_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT
    }
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10  # 限制回覆長度加快測試
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    print(f"  👉 測試 [{model_name}] ... ", end="")
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ 成功對話！")
            return True
    except urllib.error.HTTPError as e:
        # 解析 Groq 傳回的具體錯誤訊息
        try:
            error_info = json.loads(e.read().decode('utf-8'))
            error_msg = error_info.get("error", {}).get("message", "未知錯誤")
            print(f"❌ 失敗: {error_msg}")
        except:
            print(f"❌ 失敗 (HTTP {e.code})")
        return False

if __name__ == "__main__":
    if not TEST_API_KEY.startswith("gsk_"):
        print("⚠ 請先將 TEST_API_KEY 替換為你的真實金鑰")
    else:
        # 1. 取得模型清單
        available_models = get_available_models()
        
        if available_models:
            print(f"✅ 成功取得 {len(available_models)} 個文字模型，開始逐一測試 (這可能需要幾秒鐘)...\n")
            print("=" * 60)
            
            working_models = []
            # 2. 逐一測試
            for model in available_models:
                if test_model_completion(model):
                    working_models.append(model)
                time.sleep(1) # 避免打太快被限流
                
            print("=" * 60)
            
            # 3. 統整結果
            if working_models:
                print("\n🎉 測試完畢！以下模型確定可以使用：")
                for m in working_models:
                    print(f"  - {m}")
                print("\n💡 請挑選上方【任何一個】模型名稱，替換掉 GitHub 專案裡的 'model' 參數即可！")
            else:
                print("\n⚠️ 測試完畢，雖然抓得到清單，但沒有任何模型可供對話。請檢查帳號額度狀態。")