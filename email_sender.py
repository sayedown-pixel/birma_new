# email_sender.py - نسخة للـ secrets المسطح
import smtplib
import streamlit as st
from email.message import EmailMessage
from datetime import datetime

def send_weekly_report_email(recipient_email, start_date, end_date, line=None):
    try:
        from report_generator import generate_production_report_pdf
        
        # قراءة الإعدادات من التنسيق المسطح
        sender_email = st.secrets.get("sender_email", "sayedown@hotmail.com")
        sender_password = st.secrets.get("sender_password", "")
        smtp_server = st.secrets.get("smtp_server", "smtp-mail.outlook.com")
        smtp_port = st.secrets.get("smtp_port", 587)
        
        # إنشاء التقرير
        pdf_path = generate_production_report_pdf(start_date, end_date, line)
        if not pdf_path:
            return False, "لا توجد بيانات لإنشاء التقرير"
        
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
        
        # إرفاق الملف
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', 
                             filename=f'report_{datetime.now().strftime("%Y%m%d")}.pdf')
        
        # إرسال البريد
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        import os
        os.unlink(pdf_path)
        
        return True, "✅ تم إرسال التقرير بنجاح!"
        
    except Exception as e:
        return False, f"❌ فشل الإرسال: {str(e)}"