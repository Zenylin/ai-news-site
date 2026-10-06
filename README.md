# AI Daily Digest 自動化助理 🤖

這是一套基於 GitHub Actions 與 Python 打造的輕量化 AI Agent。系統會定時自動抓取指定的科技新聞 (RSS) 與股市資訊 (Yahoo Finance)，並串接 Groq API (Llama 3 模型) 進行重點摘要，最後透過 LINE Bot 推播精美的卡片訊息與文字報告至您的手機。

## 📂 專案目錄架構

```text
my-ai-agents/
├── .github/
│   └── workflows/
│       ├── stock_digest.yml      # 每天定時抓取股市與個股新聞的自動化腳本
│       └── tech_news.yml         # 每天定時抓取並摘要科技新聞的自動化腳本
├── skills/                       # 共用技能模組
│   ├── ai_summarizer.py          # Groq API 呼叫與摘要處理
│   └── notifier.py               # LINE API 訊息推播 (文字與 Flex Message)
├── fetch_stocks.py               # 股市追蹤主程式
├── fetch_news.py                 # 科技新聞追蹤主程式
├── requirements.txt              # Python 套件清單
└── README.md                     # 專案說明文件