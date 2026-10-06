import os
import time
from datetime import datetime
from imap_tools import MailBox, A
import pdfplumber

# 匯入你的共用技能
from skills.ai_summarizer import parse_credit_card_statement
from skills.notifier import send_line_text

# 環境變數
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
TAISHIN_PDF_PASSWORD = os.environ.get("TAISHIN_PDF_PASSWORD") # 身分證字號

def download_latest_statement() -> str:
    """從 Gmail 下載最新的台新信用卡對帳單 PDF"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("⚠️ 缺少 Gmail 登入資訊，跳過處理。")
        return None

    print("🔄 正在連線至 Gmail 尋找台新對帳單...")
    try:
        with MailBox('imap.gmail.com').login(GMAIL_USER, GMAIL_APP_PASSWORD) as mailbox:
            # 尋找信件標題包含「台新銀行信用卡綜合對帳單」且有附件的信
            emails = mailbox.fetch(A(subject="台新銀行信用卡綜合對帳單", has_attachment=True), limit=1, reverse=True)
            
            for msg in emails:
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        file_path = f"/tmp/{att.filename}"
                        with open(file_path, 'wb') as f:
                            f.write(att.payload)
                        print(f"✅ 成功下載對帳單：{att.filename}")
                        return file_path
    except Exception as e:
        print(f"❌ 收信失敗: {e}")
    return None

def extract_text_from_pdf(pdf_path: str) -> str:
    """使用密碼解鎖 PDF 並萃取純文字"""
    print("🔄 正在解密 PDF 並萃取文字...")
    raw_text = ""
    try:
        with pdfplumber.open(pdf_path, password=TAISHIN_PDF_PASSWORD) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
        print("✅ 文字萃取完成！")
        return raw_text
    except Exception as e:
        print(f"❌ PDF 解析失敗 (密碼錯誤或檔案毀損): {e}")
        return ""

def main():
    # 1. 下載對帳單 PDF
    pdf_path = download_latest_statement()
    if not pdf_path:
        print("沒有找到對帳單，結束任務。")
        return

    # 2. 解密並萃取文字
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        return

    # 3. 呼叫 AI 進行結構化摘要 (使用 qwen 模型)
    print("🧠 正在將對帳單交給 AI 分析...")
    transactions = parse_credit_card_statement(raw_text)
    
    if not transactions:
        print("⚠️️ AI 解析失敗或沒有找到消費紀錄。")
        return

    # 4. 組合 LINE 訊息並推播
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"💳 台新信用卡對帳單解析 ({today})\n====================\n\n"
    
    total_amount = 0
    for t in transactions:
        date = t.get("date", "未知日期")
        merchant = t.get("merchant", "未知商店")
        amount = t.get("amount", 0)
        total_amount += int(amount)
        msg += f"🔹 {date} | {merchant} | ${amount}\n"
        
    msg += f"\n💰 總計解析金額：${total_amount}"
    
    send_line_text(msg)
    print("📱 記帳推播發送成功！")

if __name__ == "__main__":
    main()