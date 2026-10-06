import os
import time
from datetime import datetime, date
from imap_tools import MailBox, A
import pdfplumber

# 匯入你的共用技能
from skills.ai_summarizer import parse_credit_card_statement
from skills.notifier import send_line_text

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
TAISHIN_PDF_PASSWORD = os.environ.get("TAISHIN_PDF_PASSWORD")

def download_yearly_statements() -> list:
    """從 Gmail 寬鬆掃描今年所有的台新對帳單 PDF"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("⚠️ 缺少 Gmail 登入資訊，跳過處理。")
        return []

    pdf_paths = []
    print("🔄 正在連線至 Gmail [全部郵件]，放寬條件搜尋 2026 年信件...")
    try:
        with MailBox('imap.gmail.com').login(GMAIL_USER, GMAIL_APP_PASSWORD) as mailbox:
            mailbox.folder.set('[Gmail]/全部郵件')
            print("📁 成功切換至資料夾：[Gmail]/全部郵件")

            # 🟢 拿掉 from_ 限制，只限制日期是 2026 年之後
            emails = mailbox.fetch(A(date_gte=date(2026, 1, 1)), reverse=True)
            
            scan_count = 0
            matched_count = 0
            for msg in emails:
                scan_count += 1
                
                # 將寄件人與主旨轉成小寫，方便不分大小寫比對
                sender = str(msg.from_).lower()
                subject = str(msg.subject)
                
                # 嚴格過濾條件：
                # 1. 寄件人必須是台新銀行官方網域
                is_taishin_official = "taishinbank.com.tw" in sender
                
                # 2. 主旨必須包含真正的帳單關鍵字（排除登入通知、轉帳、行銷廣告）
                is_statement_subject = any(keyword in subject for keyword in ["綜合對帳單", "電子帳單", "信用卡帳單", "消費明細"])
                
                if is_taishin_official and is_statement_subject:
                    matched_count += 1
                    print(f"📧 命中真正的台新帳單：[{subject}] (寄件人: {msg.from_})")
                    
                    if not msg.attachments:
                        print("     ⚠️ 這封信沒有附件")
                        continue
                        
                    for att in msg.attachments:
                        print(f"     📎 發現附件：{att.filename}")
                        if att.filename.lower().endswith('.pdf'):
                            date_str = msg.date.strftime("%Y%m%d")
                            file_path = f"/tmp/taishin_{date_str}_{att.filename}"
                            with open(file_path, 'wb') as f:
                                f.write(att.payload)
                            print(f"     ✅ 成功下載對帳單 PDF：{file_path}")
                            pdf_paths.append(file_path)
                            
            print(f"\n📊 統計：總共掃描了 {scan_count} 封 2026 年的信件，其中符合台新/帳單條件的有 {matched_count} 封。")
            
    except Exception as e:
        print(f"❌ 收信失敗: {e}")
        
    return pdf_paths

def extract_text_from_pdf(pdf_path: str) -> str:
    """使用密碼解鎖 PDF 並萃取純文字"""
    raw_text = ""
    try:
        with pdfplumber.open(pdf_path, password=TAISHIN_PDF_PASSWORD) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
        return raw_text
    except Exception as e:
        print(f"❌ PDF {pdf_path} 解析失敗: {e}")
        return ""

def main():
    # 1. 批次下載今年所有的對帳單
    pdf_paths = download_yearly_statements()
    if not pdf_paths:
        print("沒有找到對帳單，結束任務。")
        return

    all_transactions = []
    
    # 2. 逐一處理每個月份的 PDF
    print(f"\n🚀 準備解析 {len(pdf_paths)} 份對帳單...")
    for pdf_path in pdf_paths:
        print(f"🔄 正在解密與解析 {pdf_path} ...")
        raw_text = extract_text_from_pdf(pdf_path)
        
        if raw_text:
            print("  🧠 交給 AI 提取消費紀錄...")
            transactions = parse_credit_card_statement(raw_text)
            if transactions:
                all_transactions.extend(transactions)
                print(f"  ✅ 成功提取 {len(transactions)} 筆消費")
            
            # 暫停 10 秒，避免連續呼叫 Groq API 導致被限流 (HTTP 429)
            time.sleep(10) 

    if not all_transactions:
        print("⚠ AI 解析失敗或沒有找到任何消費紀錄。")
        return

    # 3. 依照日期排序
    all_transactions.sort(key=lambda x: x.get("date", ""))

    # 4. 統計與推播 (避免整年幾百筆紀錄洗版 LINE，我們只印總結與最近 15 筆)
    today = datetime.now().strftime("%Y-%m-%d")
    total_amount = 0
    
    for t in all_transactions:
        try:
            total_amount += int(t.get("amount", 0))
        except:
            pass

    tx_count = len(all_transactions)
    msg = f"💳 2026 年度信用卡對帳單總結\n====================\n"
    msg += f"✅ 共成功解析：{tx_count} 筆消費紀錄\n"
    msg += f"💰 本年度累積刷卡金額：${total_amount:,}\n\n"
    msg += "--- 最近 15 筆消費 --- \n"
    
    for t in all_transactions[-15:]:
        date_str = t.get('date', '')
        merchant = t.get('merchant', '')
        amount = t.get('amount', 0)
        msg += f"🔹 {date_str} | {merchant} | ${amount}\n"
        
    msg += "\n💡 (完整明細已存在記憶體中，下一步可設定自動寫入 Google Sheets 記帳本！)"
    
    send_line_text(msg)
    print("\n📱 年度總結推播發送成功！")

if __name__ == "__main__":
    main()
