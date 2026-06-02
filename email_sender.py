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
# email_sender.py - أضف هذه الدوال

import schedule
import time
import threading
from datetime import datetime, timedelta
from constants import WEEKLY_REPORT_RECIPIENTS

def send_weekly_auto_reports():
    """إرسال التقارير الأسبوعية التلقائية لجميع المستلمين"""
    from report_generator import generate_production_report_pdf
    from database import db_manager
    import smtplib
    from email.message import EmailMessage
    import streamlit as st
    import os
    
    print(f"🔄 Running weekly auto report at {datetime.now()}")
    
    try:
        # حساب الفترة (آخر 7 أيام)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # إنشاء التقرير
        pdf_path = generate_production_report_pdf(start_date, end_date)
        
        if not pdf_path or not os.path.exists(pdf_path):
            print("❌ Failed to generate report for auto send")
            return
        
        # قراءة إعدادات البريد
        try:
            if hasattr(st, 'secrets'):
                sender_email = st.secrets.get("sender_email", "")
                sender_password = st.secrets.get("sender_password", "")
                smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
                smtp_port = st.secrets.get("smtp_port", 587)
            else:
                sender_email = ""
                sender_password = ""
                smtp_server = "smtp.gmail.com"
                smtp_port = 587
        except:
            sender_email = ""
            sender_password = ""
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
        
        if not sender_email or not sender_password:
            print("❌ Email not configured for auto send")
            return
        
        # إرسال لجميع المستلمين
        success_count = 0
        for recipient in WEEKLY_REPORT_RECIPIENTS:
            try:
                msg = EmailMessage()
                msg['Subject'] = f'📊 التقرير الأسبوعي - نظام المصنع الذكي ({start_date.date()} إلى {end_date.date()})'
                msg['From'] = sender_email
                msg['To'] = recipient
                msg.set_content(f"""
                السادة المحترمين،
                
                يرفق هذا البريد التقرير الأسبوعي لنظام المصنع الذكي.
                
                الفترة: {start_date.date()} إلى {end_date.date()}
                
                يمكنكم الاطلاع على التفاصيل الكاملة في المرفق.
                
                مع تحيات،
                نظام المصنع الذكي
                Smart Factory System
                """)
                
                with open(pdf_path, 'rb') as f:
                    msg.add_attachment(f.read(), maintype='application', subtype='pdf', 
                                     filename=f'weekly_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf')
                
                with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                
                success_count += 1
                print(f"✅ Auto report sent to {recipient}")
                
            except Exception as e:
                print(f"❌ Failed to send to {recipient}: {e}")
        
        # حذف الملف المؤقت
        try:
            os.unlink(pdf_path)
        except:
            pass
        
        print(f"📊 Weekly auto report completed: {success_count}/{len(WEEKLY_REPORT_RECIPIENTS)} sent")
        
    except Exception as e:
        print(f"❌ Auto report error: {e}")


def start_weekly_scheduler():
    """تشغيل المجدول الأسبوعي"""
    try:
        # جدولة الإرسال كل يوم اثنين الساعة 8 صباحاً
        schedule.every().monday.at("08:00").do(send_weekly_auto_reports)
        
        # تشغيل المجدول في thread منفصل
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # التحقق كل دقيقة
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print("✅ Weekly email scheduler started (every Monday at 08:00)")
        
    except Exception as e:
        print(f"❌ Scheduler error: {e}")    