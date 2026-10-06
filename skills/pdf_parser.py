import os
import pdfplumber

def extract_text_from_pdf(pdf_path: str) -> str:
    """解密 PDF 並抓取所有文字"""
    pdf_password = os.environ.get("R124200123") # 身分證字號
    
    raw_text = ""
    try:
        # 開啟加密的 PDF
        with pdfplumber.open(pdf_path, password=pdf_password) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
        print("✅ PDF 解密與文字萃取成功！")
        return raw_text
    except Exception as e:
        print(f"❌ PDF 讀取失敗: {e}")
        return ""