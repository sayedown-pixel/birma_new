import streamlit as st
import json
import base64
import os
from datetime import datetime
from database import db_manager
from utils import USERS, LANG

def save_credentials_local(username, password, remember=True):
    """Save credentials to localStorage"""
    if remember:
        try:
            data = {"u": username, "p": password, "t": datetime.now().isoformat()}
            encoded = base64.b64encode(json.dumps(data).encode()).decode()
            st.markdown(f"<script>localStorage.setItem('sfs_creds', '{encoded}');</script>", unsafe_allow_html=True)
            return True
        except:
            return False
    return False

def load_credentials_local():
    """Load credentials safely from Streamlit session or params"""
    # تجنب إعادة توجيه الصفحة بالجافا سكريبت لعدم تعليق المتصفح
    if 'creds' in st.query_params:
        try:
            decoded = base64.b64decode(st.query_params['creds']).decode()
            data = json.loads(decoded)
            return data.get('u'), data.get('p'), True
        except:
            return None, None, False
    return None, None, False

def clear_credentials_local():
    """Clear saved credentials"""
    st.markdown("<script>localStorage.removeItem('sfs_creds');</script>", unsafe_allow_html=True)
    if 'creds' in st.query_params:
        del st.query_params['creds']

def init_session_state():
    """Initialize session state variables"""
    if 'lang' not in st.session_state:
        st.session_state.lang = 'ar'
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'inventory_version' not in st.session_state:
        st.session_state.inventory_version = 0

def login_screen(t):
    """Display login screen"""
    # التأكد من تهيئة الجلسة أولاً
    init_session_state()
    
    saved_user, saved_pass, _ = load_credentials_local()
    
    if saved_user and saved_pass:
        user = db_manager.authenticate_user(saved_user, saved_pass)
        if user:
            st.session_state.authenticated = True
            st.session_state.user_role = user['role']
            st.session_state.user_name = user['name']
            st.session_state.user_id = user['id']
            st.rerun()
    
    # عرض الشعار أو العنوان الملون
    st.markdown("<h1 style='text-align: center; color: #0047AB; font-family: sans-serif;'>🏭 Integrated System</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #555;'>نظام إدارة وتحليلات OEE</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader(t.get("login_btn", "تسجيل الدخول"))
        with st.form("login_form"):
            username = st.text_input(t.get("username", "اسم المستخدم"))
            password = st.text_input(t.get("password", "كلمة المرور"), type="password")
            remember = st.checkbox(t.get("remember_me", "تذكرني"))
            
            submit = st.form_submit_button(t.get("login_btn", "دخول"), use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("الرجاء إدخال اسم المستخدم وكلمة المرور")
                    return
                
                # التحقق عبر قاعدة البيانات (تعيد dict)
                user = db_manager.authenticate_user(username, password)
                
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_role = user['role']
                    st.session_state.user_name = user['name']
                    st.session_state.user_id = user['id']
                    if remember:
                        save_credentials_local(username, password, True)
                    st.rerun()
                else:
                    # نظام الحسابات القديمة الكلاسيكية للطوارئ
                    if username in USERS and USERS[username]["password"] == password:
                        db_manager.create_user(username, password, USERS[username]["role"], USERS[username]["name"], USERS[username]["icon"])
                        user = db_manager.authenticate_user(username, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user_role = user['role']
                            st.session_state.user_name = user['name']
                            st.session_state.user_id = user['id']
                            if remember:
                                save_credentials_local(username, password, True)
                            st.rerun()
                    else:
                        st.error(t.get("login_error", "اسم المستخدم أو كلمة المرور غير صحيحة"))

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.user_id = None
    st.rerun()

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.authenticated

def change_password(username, old_password, new_password):
    """Change user password"""
    user = db_manager.authenticate_user(username, old_password)
    if user:
        return db_manager.update_user_password(username, new_password)
    return False