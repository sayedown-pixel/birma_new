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

# email_sender.py - استبدل دالة إرسال البريد بهذه النسخة المحسنة

def send_weekly_auto_reports():
    """إرسال التقارير الأسبوعية التلقائية لجميع المستلمين (محسنة لتجنب Spam)"""
    from report_generator import generate_production_report_pdf
    import smtplib
    from email.message import EmailMessage
    from email.utils import formatdate
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
                sender_name = st.secrets.get("sender_name", "Smart Factory System")
                smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
                smtp_port = st.secrets.get("smtp_port", 587)
            else:
                sender_email = ""
                sender_password = ""
                sender_name = "Smart Factory System"
                smtp_server = "smtp.gmail.com"
                smtp_port = 587
        except:
            sender_email = ""
            sender_password = ""
            sender_name = "Smart Factory System"
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
                
                # ✅ تحسين عنوان البريد
                msg['Subject'] = f'📊 التقرير الأسبوعي لنظام المصنع الذكي - {start_date.strftime("%Y-%m-%d")} إلى {end_date.strftime("%Y-%m-%d")}'
                msg['From'] = f'{sender_name} <{sender_email}>'
                msg['To'] = recipient
                msg['Date'] = formatdate(localtime=True)
                msg['Message-ID'] = f'<{datetime.now().timestamp()}.{recipient}@smartfactory.com>'
                
                # ✅ تحسين محتوى البريد (HTML بدلاً من نص عادي)
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%); color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; }}
                        .footer {{ background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                        .info {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                        th {{ background: #1e3a5f; color: white; padding: 10px; text-align: center; }}
                        td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
                        .good {{ background: #d4edda; color: #155724; }}
                        .warning {{ background: #fff3cd; color: #856404; }}
                        .critical {{ background: #f8d7da; color: #721c24; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>🏭 نظام المصنع الذكي</h2>
                        <p>Smart Factory System</p>
                    </div>
                    <div class="content">
                        <h3>التقرير الأسبوعي</h3>
                        <p>📅 <strong>الفترة:</strong> من {start_date.strftime("%Y-%m-%d")} إلى {end_date.strftime("%Y-%m-%d")}</p>
                        <p>📊 <strong>تاريخ التقرير:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                        
                        <div class="info">
                            <p>🔍 هذا التقرير يتم إرساله تلقائياً بشكل أسبوعي ويحتوي على ملخص أداء الإنتاج والمخزون.</p>
                            <p>📎 المرفق: ملف PDF كامل بالتفاصيل</p>
                        </div>
                        
                        <p>يرجى الاطلاع على المرفق للحصول على التفاصيل الكاملة.</p>
                        
                        <hr>
                        <p style="font-size: 12px; color: #888;">
                            هذا بريد آلي من نظام المصنع الذكي. لا تتردد في الاتصال بنا لأي استفسار.
                        </p>
                    </div>
                    <div class="footer">
                        &copy; 2026 Smart Factory System | نظام متكامل لإدارة وتحليلات المصانع
                    </div>
                </body>
                </html>
                """
                
                # نص عادي بديل للعملاء الذين لا يدعمون HTML
                text_content = f"""
                التقرير الأسبوعي - نظام المصنع الذكي
                ========================================
                
                الفترة: {start_date.strftime("%Y-%m-%d")} إلى {end_date.strftime("%Y-%m-%d")}
                تاريخ التقرير: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                
                هذا التقرير يتم إرساله تلقائياً بشكل أسبوعي.
                
                يرجى الاطلاع على المرفق للحصول على التفاصيل الكاملة.
                
                --
                Smart Factory System
                نظام إدارة وتحليلات المصانع
                """
                
                # إضافة المحتوى بنوعين (HTML و plain text)
                msg.add_alternative(text_content, subtype='plain')
                msg.add_alternative(html_content, subtype='html')
                
                # إرفاق PDF
                with open(pdf_path, 'rb') as f:
                    msg.add_attachment(
                        f.read(), 
                        maintype='application', 
                        subtype='pdf',
                        filename=f'weekly_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'
                    )
                
                # إرسال البريد
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


# email_sender.py - ابحث عن هذه الأسطر وقم بتعليقها

# def start_weekly_scheduler():
#     """تشغيل المجدول الأسبوعي"""
#     try:
#         schedule.every().monday.at("08:00").do(send_weekly_auto_reports)
#         
#         def run_scheduler():
#             while True:
#                 schedule.run_pending()
#                 time.sleep(60)
#         
#         scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
#         scheduler_thread.start()
#         print("✅ Weekly email scheduler started (every Monday at 08:00)")
#     except Exception as e:
#         print(f"❌ Scheduler error: {e}")

# ❌ قم بتعليق السطر الذي يستدعيها في app.py 