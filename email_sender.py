# email_sender.py - نسخة نهائية تعمل

import streamlit as st
import smtplib
import os
from email.message import EmailMessage
from datetime import datetime
from report_generator import generate_production_report_pdf

def send_weekly_report_email(recipient_email, start_date, end_date, line=None):
    """إرسال تقرير أسبوعي عبر البريد الإلكتروني"""
    
    # ✅ طريقة مبسطة لقراءة الإعدادات
    sender_email = None
    sender_password = None
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    # محاولة قراءة من st.secrets
    try:
        if hasattr(st, 'secrets'):
            # طباعة للمساعدة في التصحيح
            print("🔍 st.secrets found")
            print(f"   Keys: {list(st.secrets.keys())}")
            
            # محاولة قراءة بطرق مختلفة
            if 'sender_email' in st.secrets:
                sender_email = st.secrets['sender_email']
                sender_password = st.secrets['sender_password']
                smtp_server = st.secrets.get('smtp_server', 'smtp.gmail.com')
                smtp_port = st.secrets.get('smtp_port', 587)
                print("✅ Email settings loaded from flat keys")
            elif 'email' in st.secrets:
                sender_email = st.secrets['email'].get('sender_email')
                sender_password = st.secrets['email'].get('sender_password')
                smtp_server = st.secrets['email'].get('smtp_server', 'smtp.gmail.com')
                smtp_port = st.secrets['email'].get('smtp_port', 587)
                print("✅ Email settings loaded from nested 'email' section")
    except Exception as e:
        print(f"❌ Error reading secrets: {e}")
    
    # ✅ إذا لم يتم العثور على الإعدادات، اعرض رسالة واضحة
    if not sender_email or not sender_password:
        st.error("""
        ⚠️ **لم يتم تكوين إعدادات البريد الإلكتروني!**
        
        يرجى إنشاء ملف `.streamlit/secrets.toml` بالمحتوى التالي:
        
        ```toml
        sender_email = "your_email@gmail.com"
        sender_password = "your_app_password"
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        """)