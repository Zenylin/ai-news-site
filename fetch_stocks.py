def call_groq_api(prompt, retries=3):
    if not GROQ_API_KEY:
        raise Exception("❌ 未偵測到 GROQ_API_KEY")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'User-Agent': USER_AGENT
    }

    fallback_models = [
        "qwen/qwen3.8-27b", 
        "openai/gpt-oss-120b", 
        "openai/gpt-oss-20b",
        "allam-2-7b"
    ]

    for model_name in fallback_models:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "你是一個專業的財經編輯，請嚴格只輸出合法的 JSON 格式內容。"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)

        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    return json.loads(result['choices'][0]['message']['content'])
            except urllib.error.HTTPError as e:
                if e.code in [404, 400]:
                    print(f"⚠️ 股票摘要: 模型 {model_name} 不支援，自動換下一個...")
                    break # 直接切換下一個模型
                time.sleep(3)
                
    return None