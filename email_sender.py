# email_sender.py - نسخة مستقرة

import streamlit as st
import smtplib
import os
from email.message import EmailMessage
from datetime import datetime
from report_generator import generate_production_report_pdf

def send_weekly_report_email(recipient_email, start_date, end_date, line=None):
    """إرسال تقرير أسبوعي عبر البريد الإلكتروني"""
    
    # قيمة افتراضية للدالة (يجب أن تعيد tuple دائماً)
    sender_email = None
    sender_password = None
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    # محاولة قراءة الإعدادات
    try:
        if hasattr(st, 'secrets'):
            # محاولة قراءة مباشرة
            if 'sender_email' in st.secrets:
                sender_email = st.secrets['sender_email']
                sender_password = st.secrets['sender_password']
                smtp_server = st.secrets.get('smtp_server', 'smtp.gmail.com')
                smtp_port = st.secrets.get('smtp_port', 587)
            elif 'email' in st.secrets:
                sender_email = st.secrets['email'].get('sender_email')
                sender_password = st.secrets['email'].get('sender_password')
                smtp_server = st.secrets['email'].get('smtp_server', 'smtp.gmail.com')
                smtp_port = st.secrets['email'].get('smtp_port', 587)
    except Exception as e:
        print(f"Error reading secrets: {e}")
    
    # التحقق من وجود الإعدادات
    if not sender_email or not sender_password:
        # ✅ عرض رسالة خطأ للمستخدم وإرجاع tuple
        st.warning("⚠️ لم يتم تكوين إعدادات البريد الإلكتروني. يرجى إضافة sender_email و sender_password في secrets.toml")
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
        
        # حذف الملف المؤقت
        import os
        os.unlink(pdf_path)
        
        return True, "✅ تم إرسال التقرير بنجاح!"
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ فشل المصادقة: تحقق من البريد الإلكتروني وكلمة المرور"
    except Exception as e:
        return False, f"❌ فشل الإرسال: {str(e)}"