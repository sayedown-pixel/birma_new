

# email_sender.py

import streamlit as st
import smtplib
import os
from email.message import EmailMessage
from datetime import datetime
from report_generator import generate_production_report_pdf
def send_email_via_smtp(recipient, subject, body, attachment_path=None):
    
    try:
        # الطريقة الأولى: قراءة مباشرة
        email = st.secrets["sender_email"]
        password = st.secrets["sender_password"]
        smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets.get("smtp_port", 587)
        print("✅ Secrets loaded successfully using direct keys.")
    except Exception as e1:
        print(f"⚠️ Direct key read failed: {e1}")
        try:
            # الطريقة الثانية: قراءة من خلال قاموس فرعي (مثل [email])
            email = st.secrets["email"]["sender_email"]
            password = st.secrets["email"]["sender_password"]
            smtp_server = st.secrets["email"].get("smtp_server", "smtp.gmail.com")
            smtp_port = st.secrets["email"].get("smtp_port", 587)
            print("✅ Secrets loaded successfully using nested keys.")
        except Exception as e2:
            print(f"❌ All methods failed to load secrets.")
            return False, "فشل تحميل إعدادات البريد الإلكتروني"

def get_email_config():
    """الحصول على إعدادات البريد من مصادر مختلفة"""
    # محاولة من st.secrets أولاً
    try:
        if hasattr(st, 'secrets'):
            sender_email = st.secrets.get("sender_email", "")
            sender_password = st.secrets.get("sender_password", "")
            smtp_server = st.secrets.get("smtp_server", "")
            smtp_port = st.secrets.get("smtp_port", "")
            
            if sender_email and sender_password:
                return sender_email, sender_password, smtp_server, smtp_port
    except:
        pass
    
    # محاولة من متغيرات البيئة
    sender_email = os.environ.get("SENDER_EMAIL", "")
    sender_password = os.environ.get("SENDER_PASSWORD", "")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = os.environ.get("SMTP_PORT", 587)
    
    if sender_email and sender_password:
        return sender_email, sender_password, smtp_server, smtp_port
    
    # محاولة من st.secrets بطريقة مختلفة
    try:
        if hasattr(st, 'secrets') and 'sender_email' in st.secrets:
            return st.secrets['sender_email'], st.secrets['sender_password'], 'smtp.gmail.com', 587
    except:
        pass
    
    return None, None, None, None

def send_weekly_report_email(recipient_email, start_date, end_date, line=None):
    """إرسال تقرير أسبوعي عبر البريد الإلكتروني"""
    
    # الحصول على الإعدادات
    sender_email, sender_password, smtp_server, smtp_port = get_email_config()
    
    if not sender_email or not sender_password:
        # عرض رسالة للمستخدم بدلاً من إرجاع خطأ
        st.info("📧 لإرسال التقارير عبر البريد، يرجى تكوين إعدادات SMTP في secrets.toml")
        return False, "⚠️ لم يتم تكوين إعدادات البريد الإلكتروني"
    
    try:
        # إنشاء التقرير
        pdf_path = generate_production_report_pdf(start_date, end_date, line)
        
        if not pdf_path:
            return False, "❌ فشل إنشاء التقرير"
        
        # إنشاء البريد
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
        
        # إرسال البريد
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
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