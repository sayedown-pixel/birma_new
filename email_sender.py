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
    """
    إرسال تقرير أسبوعي عبر البريد الإلكتروني
    """
    try:
        from report_generator import generate_production_report_pdf
        
        # قراءة الإعدادات من st.secrets
        try:
            sender_email = st.secrets.get("sender_email", "")
            sender_password = st.secrets.get("sender_password", "")
            smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
            smtp_port = st.secrets.get("smtp_port", 587)
        except:
            # إعدادات افتراضية للاختبار
            sender_email = "your_email@gmail.com"
            sender_password = "your_password"
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
        
        if not sender_email or not sender_password:
            return False, "⚠️ لم يتم تكوين إعدادات البريد الإلكتروني. يرجى إضافة sender_email و sender_password في secrets.toml"
        
        # إنشاء التقرير وحفظه في مجلد محدد
        pdf_path = generate_production_report_pdf(start_date, end_date, line)
        
        if not pdf_path or not os.path.exists(pdf_path):
            return False, "❌ فشل إنشاء التقرير أو الملف غير موجود"
        
        # نسخ الملف إلى مجلد التقارير لضمان بقائه
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_pdf_path = os.path.join(REPORT_DIR, f"report_{timestamp}.pdf")
        
        # نسخ الملف
        import shutil
        shutil.copy2(pdf_path, safe_pdf_path)
        
        # إنشاء البريد الإلكتروني
        msg = EmailMessage()
        msg['Subject'] = f'تقرير الإنتاج الأسبوعي ({start_date.strftime("%Y-%m-%d")} إلى {end_date.strftime("%Y-%m-%d")})'
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # نص البريد
        email_body = f"""
        السادة المديرين،

        يرفق هذا البريد تقرير الإنتاج الأسبوعي للفترة من {start_date.strftime("%Y-%m-%d")} إلى {end_date.strftime("%Y-%m-%d")}.

        تفاصيل التقرير:
        - الفترة: {start_date.strftime("%Y-%m-%d")} إلى {end_date.strftime("%Y-%m-%d")}
        - {'الخط: ' + line if line else 'جميع الخطوط'}
        - تاريخ الإنشاء: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        مع تحيات،
        نظام المصنع الذكي - Smart Factory System
        """
        
        msg.set_content(email_body)
        
        # إرفاق الملف
        with open(safe_pdf_path, 'rb') as f:
            msg.add_attachment(
                f.read(),
                maintype='application',
                subtype='pdf',
                filename=f'report_{timestamp}.pdf'
            )
        
        # إرسال البريد
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        # تنظيف الملفات المؤقتة (اختياري - احتفظ بها للتصحيح)
        try:
            os.unlink(pdf_path)  # حذف الملف المؤقت الأصلي
        except:
            pass
        
        return True, f"✅ تم إرسال التقرير بنجاح إلى {recipient_email}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ فشل المصادقة: يرجى التحقق من البريد الإلكتروني وكلمة المرور"
    except smtplib.SMTPException as e:
        return False, f"❌ خطأ في SMTP: {str(e)}"
    except Exception as e:
        return False, f"❌ فشل الإرسال: {str(e)}"