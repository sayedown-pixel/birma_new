# email_sender.py - نسخة محسنة
import smtplib
import streamlit as st
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import os
import tempfile

# إنشاء مجلد للتقارير المؤقتة
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def send_weekly_report_email(recipient_email, start_date, end_date, line=None):
    """إرسال تقرير أسبوعي عبر البريد الإلكتروني"""
    
    sender_email = st.secrets.get("sender_email", "")
    sender_password = st.secrets.get("sender_password", "")
    smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
    smtp_port = st.secrets.get("smtp_port", 587)
    if not sender_email or not sender_password:
            return False, "⚠️ لم يتم تكوين إعدادات البريد الإلكتروني"
        
    try:
        from report_generator import generate_production_report_pdf
        
        pdf_path = generate_production_report_pdf(start_date, end_date, line)
        
        if not pdf_path:
            return False, "❌ فشل إنشاء التقرير"
        
        msg = EmailMessage()
        msg['Subject'] = f'تقرير الإنتاج الأسبوعي ({start_date.date()} إلى {end_date.date()})'
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg.set_content(f"""
        السادة المديرين،

        يرفق هذا البريد تقرير الإنتاج الأسبوعي للفترة من {start_date.date()} إلى {end_date.date()}.

        مع تحيات،
        نظام المصنع الذكي
        """)
        
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', 
                             filename=f'report_{datetime.now().strftime("%Y%m%d")}.pdf')
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        import os
        os.unlink(pdf_path)
        
        return True, "✅ تم إرسال التقرير بنجاح!"
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ فشل المصادقة: تحقق من البريد الإلكتروني وكلمة المرور"
    except Exception as e:
        return False, f"❌ فشل الإرسال: {str(e)}"
