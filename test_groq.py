from imap_tools import MailBox, A

# 🟢 請填入你的 Gmail 與 16 碼應用程式密碼
GMAIL_ACCOUNT = "joo99887@gmail.com"
GMAIL_APP_PASSWORD = "juhvqhdofrajzmpk"

def test_download_pdf():
    print("🔄 嘗試連線到 Gmail IMAP 伺服器...")
    try:
        # 登入 Gmail
        with MailBox('imap.gmail.com').login(GMAIL_ACCOUNT, GMAIL_APP_PASSWORD) as mailbox:
            print("✅ 登入成功！正在尋找信件...\n")
            
            # 尋找最新 3 封「帶有附件」的信件
            # 如果你要針對台新，可以改成 A(subject="台新", has_attachment=True)
            emails = mailbox.fetch(A(has_attachment=True), limit=3, reverse=True)
            
            found_pdf = False
            for msg in emails:
                print(f"📧 檢查信件：{msg.subject}")
                
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        print(f"  👉 發現 PDF 附件：{att.filename}")
                        
                        # 將檔案存到你執行程式的當前資料夾
                        save_path = f"./{att.filename}"
                        with open(save_path, 'wb') as f:
                            f.write(att.payload)
                            
                        print(f"  🎉 成功下載並儲存至：{save_path}\n")
                        found_pdf = True
                        break # 載到一個就跳出附件迴圈
                
                if found_pdf:
                    break # 測試成功，跳出信件迴圈
            
            if not found_pdf:
                print("⚠️ 最近的信件中沒有找到 PDF 附件。建議你先用其他信箱寄一封帶有 PDF 的信給自己測試！")
                
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        print("💡 提示：如果是 Authentication Failed，請確認是否使用了「應用程式密碼」而非原本的登入密碼。")

if __name__ == "__main__":
    test_download_pdf()