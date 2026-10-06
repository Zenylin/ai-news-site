import os
from imap_tools import MailBox, A

def download_taishin_statement():
    """搜尋台新對帳單信件，並下載 PDF 附件"""
    email_user = os.environ.get("GMAIL_USER")
    email_pass = os.environ.get("GMAIL_APP_PASSWORD")
    
    # 登入 Gmail
    with MailBox('imap.gmail.com').login(email_user, email_pass) as mailbox:
        # 尋找信件標題包含「台新銀行信用卡綜合對帳單」的信件
        for msg in mailbox.fetch(A(subject="台新銀行", has_attachment=True), limit=1, reverse=True):
            for att in msg.attachments:
                if att.filename.lower().endswith('.pdf'):
                    file_path = f"/tmp/{att.filename}"
                    with open(file_path, 'wb') as f:
                        f.write(att.payload)
                    print(f"✅ 成功下載對帳單：{att.filename}")
                    return file_path
    return None

#qelg laoh ubwj gpws