# auth.py - النسخة الكاملة مع نظام تسجيل الأحداث

import streamlit as st
import json
import base64
import os
from datetime import datetime
from database import db_manager
from constants import USERS, LANG
from helpers import load_language

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
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'inventory_version' not in st.session_state:
        st.session_state.inventory_version = 0
    if 'must_change_password' not in st.session_state:
        st.session_state.must_change_password = False

def force_change_password_screen():
    """شاشة إجبارية لتغيير كلمة المرور عند أول تسجيل دخول"""
    
    # تحميل الترجمة
    lang = st.session_state.get('lang', 'ar')
    from helpers import load_language
    t = load_language(lang)
    
    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <span style="font-size: 4rem;">🔐</span>
        <h2 style="color: #0047AB;">{t.get('force_change_title', 'Change Your Password')}</h2>
        <p style="color: #666;">{t.get('force_change_message', 'For security reasons, you must change your default password before continuing.')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("force_change_form"):
            current_password = st.text_input(
                t.get("current_password", "Current Password"), 
                type="password",
                placeholder=t.get("enter_current_password", "Enter your current password"),
                key="force_current_pw"
            )
            new_password = st.text_input(
                t.get("new_password", "New Password"), 
                type="password",
                placeholder=t.get("new_password_requirements", "Minimum 4 characters"),
                key="force_new_pw"
            )
            confirm_password = st.text_input(
                t.get("confirm_password", "Confirm New Password"), 
                type="password",
                placeholder=t.get("confirm_new_password", "Re-enter new password"),
                key="force_confirm_pw"
            )
            
            st.caption("🔒 " + t.get("password_requirements", "Password must be at least 4 characters and different from default password"))
            
            submitted = st.form_submit_button(
                t.get("change_and_continue", "✅ Change Password & Continue"), 
                width='stretch',
                type="primary"
            )
            
            if submitted:
                if not current_password or not new_password or not confirm_password:
                    st.error(t.get("fill_all_fields", "⚠️ Please fill all fields"))
                elif new_password != confirm_password:
                    st.error(t.get("passwords_mismatch", "⚠️ New passwords do not match"))
                elif len(new_password) < 4:
                    st.error(t.get("password_too_short", "⚠️ Password must be at least 4 characters"))
                elif current_password == new_password:
                    st.error(t.get("same_password", "⚠️ New password must be different from current password"))
                else:
                    username = st.session_state.get('username', '') or st.session_state.get('user_name', '')
                    
                    from database import db_manager
                    from database import User
                    import bcrypt
                    
                    session = None
                    try:
                        session = db_manager.get_session()
                        user = session.query(User).filter(User.username == username).first()
                        
                        if not user:
                            st.error(t.get("user_not_found", "❌ User not found"))
                        else:
                            is_valid = bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8'))
                            
                            if not is_valid:
                                st.error(t.get("wrong_current_password", "❌ Current password is incorrect"))
                            else:
                                new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                user.password_hash = new_hash
                                user.must_change_password = False
                                user.last_password_change = datetime.now()
                                session.commit()
                                
                                st.session_state.must_change_password = False
                                st.success(t.get("password_changed_success", "✅ Password changed successfully!"))
                                st.balloons()
                                st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                    finally:
                        if session:
                            session.close()
        
        if st.button(t.get("logout_btn", "🚪 Logout"), width='stretch'):
            logout()

def login_screen(t):
    """Display login screen"""
    init_session_state()

    # Language selector at top of login page
    col_lang1, col_lang2, col_lang3 = st.columns([1, 2, 1])
    with col_lang1:
        current_lang = st.session_state.get('lang', 'ar')
        if current_lang == 'ar':
            if st.button("🇬🇧 " + t.get("english_btn", "English"), width='stretch'):
                st.session_state.lang = 'en'
                st.session_state.t = load_language('en')
                st.rerun()
        else:
            if st.button("🇸🇦 " + t.get("arabic_btn", "Arabic"), width='stretch'):
                st.session_state.lang = 'ar'
                st.session_state.t = load_language('ar')
                st.rerun()

    saved_user, saved_pass, _ = load_credentials_local()
    
    if saved_user and saved_pass:
        user = db_manager.authenticate_user(saved_user, saved_pass)
        if user:
            st.session_state.authenticated = True
            st.session_state.user_role = user['role']
            st.session_state.user_name = user['name']
            st.session_state.username = user['username']
            st.session_state.user_id = user['id']
            #st.session_state.must_change_password = user.get('must_change_password', False)
            
            # تسجيل دخول ناجح
            try:
                if hasattr(db_manager, 'add_info_log'):
                    db_manager.add_info_log('login', f"User '{saved_user}' logged in automatically", f"Role: {user['role']}")
            except:
                pass
            
            st.rerun()
            return
    
    st.markdown(f"<h1 style='text-align: center; color: #0047AB; font-family: sans-serif;'>🏭 {t.get('app_title', 'Smart Factory System')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #555;'>{t.get('system_subtitle', 'OEE Management & Analytics System')}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader(t.get("login_btn", "Login"))
        with st.form("login_form"):
            username = st.text_input(t.get("username", "Username"))
            password = st.text_input(t.get("password", "Password"), type="password")
            remember = st.checkbox(t.get("remember_me", "Remember me"))
            
            submit = st.form_submit_button(t.get("login_btn", "Login"), width='stretch')
            
            if submit:
                if not username or not password:
                    st.error(t.get("login_validation_error", "Please enter username and password"))
                    return
                
                user = db_manager.authenticate_user(username, password)
                
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_role = user['role']
                    st.session_state.user_name = user['name']
                    st.session_state.username = user['username']
                    st.session_state.user_id = user['id']
                    # st.session_state.must_change_password = user.get('must_change_password', False)
                    
                    # تسجيل دخول ناجح
                    try:
                        if hasattr(db_manager, 'add_info_log'):
                            db_manager.add_info_log('login', f"User '{username}' logged in successfully", f"Role: {user['role']}")
                    except:
                        pass
                    
                    if remember:
                        save_credentials_local(username, password, True)
                    st.rerun()
                    return
                else:
                    # نظام الحسابات القديمة للطوارئ
                    if username in USERS and USERS[username]["password"] == password:
                        db_manager.create_user(username, password, USERS[username]["role"], USERS[username]["name"], USERS[username]["icon"])
                        user = db_manager.authenticate_user(username, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user_role = user['role']
                            st.session_state.user_name = user['name']
                            st.session_state.username = user['username']
                            st.session_state.user_id = user['id']
                           #  st.session_state.must_change_password = user.get('must_change_password', False)
                            
                            try:
                                if hasattr(db_manager, 'add_info_log'):
                                    db_manager.add_info_log('login', f"User '{username}' logged in (legacy)", f"Role: {user['role']}")
                            except:
                                pass
                            
                            if remember:
                                save_credentials_local(username, password, True)
                            st.rerun()
                            return
                    else:
                        # تسجيل محاولة فاشلة
                        try:
                            if hasattr(db_manager, 'add_warning_log'):
                                db_manager.add_warning_log('login', f"Failed login attempt for user '{username}'", "Invalid password")
                        except:
                            pass
                        st.error(t.get("login_error", "Invalid username or password"))

def logout():
    """Logout user"""
    username = st.session_state.get('username', '') or st.session_state.get('user_name', '')
    
    # تسجيل حدث الخروج
    try:
        from database import db_manager
        if hasattr(db_manager, 'add_info_log'):
            db_manager.add_info_log('logout', f"User '{username}' logged out")
    except Exception as e:
        print(f"Logout log error: {e}")
    
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.must_change_password = False
    st.rerun()

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def change_password(username, old_password, new_password):
    """Change user password"""
    user = db_manager.authenticate_user(username, old_password)
    if user:
        success = db_manager.update_user_password(username, new_password)
        if success:
            try:
                if hasattr(db_manager, 'add_info_log'):
                    db_manager.add_info_log('password', f"User '{username}' changed password")
            except:
                pass
        return success
    return False