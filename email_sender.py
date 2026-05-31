# email_sender.py - نسخة معدلة لقراءة المفاتيح من المستوى الرئيسي

import streamlit as st
import smtplib
import os
from email.message import EmailMessage
from datetime import datetime
from report_generator import generate_production_report_pdf

def send_weekly_report_email(recipient_email, start_date, end_date, line=None):
    """إرسال تقرير أسبوعي عبر البريد الإلكتروني"""
    
    # ✅ قراءة مباشرة من المستوى الرئيسي
    try:
        sender_email = st.secrets["sender_email"]
        sender_password = st.secrets["sender_password"]
        smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets.get("smtp_port", 587)
        
        print(f"✅ Email settings loaded from secrets")
        print(f"   sender_email: {sender_email}")
        
    except Exception as e:
        print(f"❌ Error reading secrets: {e}")
        st.error(f"⚠️ خطأ في قراءة إعدادات البريد: {e}")
        return False, f"⚠️ خطأ في إعدادات البريد: {e}"
    
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
        
        st.success("✅ تم إرسال التقرير بنجاح!")
        return True, "✅ تم إرسال التقرير بنجاح!"
        
    except smtplib.SMTPAuthenticationError:
        st.error("❌ فشل المصادقة: تحقق من البريد الإلكتروني وكلمة المرور")
        return False, "❌ فشل المصادقة: تحقق من البريد الإلكتروني"
    except Exception as e:
        st.error(f"❌ فشل الإرسال: {str(e)}")
        return False, f"❌ فشل الإرسال: {str(e)}"