import streamlit as st
import pandas as pd
from datetime import datetime
import os

from auth import init_session_state, login_screen, logout
from database import db_manager
from utils import load_language, LANG, ROLE_PERMISSIONS, USERS
from dashboard import show_dashboard
from production import show_production
from maintenance import show_maintenance
from records import show_records
from inventory import (
    show_raw_materials, show_finished_goods,
    load_raw_materials, load_finished_goods,
    register_inventory_cache_invalidator,
)
from admin import show_users, show_settings, show_delete_records
from oee_analytics import show_oee_dashboard
# Debug: طباعة secrets keys
try:
    st.write("🔍 Available secrets keys:", list(st.secrets.keys()))
except:
    st.write("No secrets found")
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
try:
    from database import db_manager
    if db_manager.is_connected():
        st.success("✅ متصل بقاعدة البيانات بنجاح")
        if db_manager.is_using_sqlite():
            st.info("📌 يستخدم SQLite محلياً")
        else:
            st.info("📌 يستخدم PostgreSQL")
    else:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {db_manager.get_init_error()}")
except Exception as e:
    st.error(f"❌ خطأ في قاعدة البيانات: {e}")

# ============================================================================
# Page configuration
# ============================================================================
st.set_page_config(
    page_title="BIRMA Integrated System",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Custom CSS
# ============================================================================

def apply_custom_css():
    st.markdown("""
    <style>
    /* تنسيق الهيدر */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        padding: 1rem 2rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .logo-section {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .logo-icon {
        font-size: 2.5rem;
        filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));
    }
    
    .company-title {
        color: white;
    }
    
    .company-title h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    .company-title p {
        margin: 0;
        font-size: 0.8rem;
        opacity: 0.8;
    }
    
    .user-section {
        color: white;
        text-align: right;
    }
    
    .user-name {
        font-weight: bold;
        font-size: 1rem;
    }
    
    .user-role {
        font-size: 0.8rem;
        opacity: 0.8;
    }
    
    /* شريط التوصيات */
    .marquee-container {
        background: #2d3748;
        color: white;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
        overflow: hidden;
        white-space: nowrap;
    }
    
    .marquee-content {
        display: inline-block;
        animation: marquee 40s linear infinite;
    }
    
    @keyframes marquee {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    .marquee-content span {
        margin: 0 25px;
    }
    
    .critical { color: #fc8181; font-weight: bold; }
    .warning { color: #fbbf24; }
    .success { color: #68d391; }
    .info { color: #63b3ed; }
    
    /* بطاقات المهام */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* تحسين السايدبار */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a202c 0%, #0f172a 100%);
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #e2e8f0;
    }
    
    [data-testid="stSidebar"] .stSelectbox label {
        color: #e2e8f0 !important;
    }
    
    /* تحسين الأزرار */
    .stButton button {
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton button:hover {
        transform: scale(1.02) !important;
    }
    
    /* تحسين الجداول */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    
    /* تحسين التبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 16px;
        background: #e2e8f0;
    }
    
    .stTabs [aria-selected="true"] {
        background: #2c5282;
        color: white;
    }
    
    /* footer */
    .footer {
        text-align: center;
        padding: 1rem;
        margin-top: 2rem;
        color: #718096;
        font-size: 0.8rem;
        border-top: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# Sidebar navigation
# ============================================================================

# app.py - قم بتحديث دالة show_sidebar فقط

def show_sidebar(t):
    """بناء القائمة الجانبية"""
    role = st.session_state.get('user_role', 'supervisor')
    allowed_pages = ROLE_PERMISSIONS.get(role, [])

    with st.sidebar:
        # شعار صغير في السايدبار
        st.markdown("""
        <div style="text-align: center; padding: 10px 0;">
            <span style="font-size: 3rem;">🏭</span>
            <h3 style="color: white; margin: 0;">BIRMA</h3>
            <p style="color: #a0aec0; font-size: 0.7rem;">Integrated System</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # اختيار اللغة والوضع
        col_l, col_d = st.columns(2)
        with col_l:
            current_lang = st.session_state.get('lang', 'ar')
            # زر تبديل اللغة - يتغير نصه حسب اللغة الحالية
            if current_lang == 'ar':
                if st.button("🇬🇧 English", use_container_width=True):
                    st.session_state.lang = 'en'
                    st.session_state.t = load_language('en')
                    st.rerun()
            else:
                if st.button("🇸🇦 عربي", use_container_width=True):
                    st.session_state.lang = 'ar'
                    st.session_state.t = load_language('ar')
                    st.rerun()
        
        with col_d:
            dark = st.session_state.get('dark_mode', False)
            dark_label = "🌙" if not dark else "☀️"
            if st.button(dark_label, use_container_width=True):
                st.session_state.dark_mode = not dark
        
        st.markdown("---")
        
        # قائمة الصفحات - تستخدم الترجمة الجديدة
        page_mapping = {
            "🏠 Dashboard": t.get("dashboard", "🏠 Dashboard"),
            "📈 Production": t.get("production", "📈 Production"),
            "🔧 Maintenance": t.get("maintenance", "🔧 Maintenance"),
            "📊 Records": t.get("records", "📊 Records"),
            "📦 Raw Materials": t.get("raw_materials", "📦 Raw Materials"),
            "🏭 Finished Goods": t.get("finished_goods", "🏭 Finished Goods"),
            "👥 Users": t.get("users", "👥 Users"),
            "⚙️ Settings": t.get("settings", "⚙️ Settings"),
        }
        
        # إنشاء قائمة الخيارات المعروضة
        page_options = []
        page_keys = []
        for page_key in ["🏠 Dashboard", "📈 Production", "🔧 Maintenance", "📊 Records", 
                         "📦 Raw Materials", "🏭 Finished Goods", "👥 Users", "⚙️ Settings"]:
            if page_key in allowed_pages:
                page_options.append(page_mapping.get(page_key, page_key))
                page_keys.append(page_key)
        
        # استخدام radio مع القائمة المعروضة
        selected_display = st.radio(
            t.get("menu", "القائمة"),
            page_options,
            label_visibility="collapsed"
        )
        
        # إعادة تحويل النص المعروض إلى المفتاح الأصلي
        if selected_display in page_options:
            selected_page = page_keys[page_options.index(selected_display)]
        else:
            selected_page = page_options[0] if page_options else "🏠 Dashboard"
        
        # اختيار خط الإنتاج
        selected_line = None
        if selected_page in ["📈 Production", "🔧 Maintenance", "🏠 Dashboard"]:
            st.markdown("---")
            line_options = ["الخط الأول(smi)", "الخط الثاني(welbing)"]
            line_labels = [t.get("line1", "الخط الأول(smi)"), t.get("line2", "الخط الثاني(welbing)")]
            selected_line = st.selectbox(
                t.get("line_label", "خط الإنتاج"),
                line_options,
                format_func=lambda x: line_labels[line_options.index(x)],
                key="line_select"
            )
        
        # معلومات الاتصال بقاعدة البيانات
        st.markdown("---")
        if db_manager.is_connected():
            db_status = "✅ " + t.get("connected", "متصل")
            db_type = "SQLite" if db_manager._use_sqlite else "PostgreSQL"
            st.caption(f"💾 {db_type}: {db_status}")
        else:
            st.caption("💾 DB: ❌ " + t.get("disconnected", "غير متصل"))
        
        st.caption(f"© {datetime.now().year} BIRMA System")
    
    return selected_page, selected_line

# ============================================================================
# Load inventory data
# ============================================================================

@st.cache_data(show_spinner=False)
def _load_inventory_cached(inventory_version: int):
    """تحميل المخزون من Excel — يُحدَّث عند تغيير inventory_version فقط."""
    return load_raw_materials(), load_finished_goods()


def load_inventory_data():
    version = st.session_state.get("inventory_version", 0)
    return _load_inventory_cached(version)


register_inventory_cache_invalidator(_load_inventory_cached.clear)

# ============================================================================
# Main application
# ============================================================================

def main():
    # تطبيق التنسيقات
    apply_custom_css()
    
    # تهيئة الجلسة
    init_session_state()
    
    # التحقق من اتصال قاعدة البيانات
    if not db_manager.is_connected():
        st.error(f"❌ تعذر الاتصال بقاعدة البيانات: {db_manager.get_init_error()}")
        st.info("سيتم استخدام SQLite كقاعدة بيانات محلية. سيتم إنشاء ملف birma_data.db تلقائياً.")
    
    # شاشة تسجيل الدخول
    if not st.session_state.get('authenticated', False):
        login_screen(LANG["ar"])
        return
    
    # تحميل اللغة
    lang = st.session_state.get('lang', 'ar')
    t = load_language(lang)
    
    # تحميل بيانات المخزون
    df_raw, df_fg = load_inventory_data()
    
    if df_raw is None or df_raw.empty:
        st.sidebar.warning("⚠️ ملف المواد الخام غير موجود أو فارغ")
        df_raw = pd.DataFrame()
    
    if df_fg is None or df_fg.empty:
        st.sidebar.warning("⚠️ ملف المنتج التام غير موجود أو فارغ")
        df_fg = pd.DataFrame()
    
    # ======================================================================
    # Header with Logo
    # ======================================================================
    
    user_name = st.session_state.get('user_name', '')
    user_role = st.session_state.get('user_role', '')
    
    st.markdown(f"""
    <div class="main-header">
        <div class="logo-section">
            <span class="logo-icon">🏭</span>
            <div class="company-title">
                <h1>BIRMA Integrated System</h1>
                <p>{t.get('designer', 'نظام إدارة وتحليلات OEE')}</p>
            </div>
        </div>
        <div class="user-section">
            <div class="user-name">👤 {user_name}</div>
            <div class="user-role">{user_role}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # زر تسجيل الخروج في أعلى اليمين
    col1, col2, col3 = st.columns([5, 1, 1])
    with col3:
        if st.button("🚪 " + t.get('logout_btn', 'خروج'), use_container_width=True):
            logout()
    
    # ======================================================================
    # Sidebar and Navigation
    # ======================================================================
    selected_page, selected_line = show_sidebar(t)
    
    if not selected_line:
        selected_line = "الخط الأول(smi)"
    
    # تحميل بيانات الإنتاج للصفحات التي تحتاجها
    df_main = pd.DataFrame()
    if selected_page in ["🏠 Dashboard", "📈 Production", "🔧 Maintenance"]:
        try:
            df_main = db_manager.get_all_production()
        except Exception as e:
            st.warning(f"تعذر تحميل بيانات الإنتاج: {e}")
    
    # ======================================================================
    # Page Routing
    # ======================================================================
    
    if selected_page == "🏠 Dashboard":
        show_dashboard(df_main, df_raw, df_fg, t, selected_line)
    
    elif selected_page == "📈 Production":
        show_production(selected_line, df_raw, df_fg, t)
    
    elif selected_page == "🔧 Maintenance":
        show_maintenance(selected_line, t)
    
    elif selected_page == "📊 Records":
        show_records(t, lang, df_raw, df_fg)
    
    elif selected_page == "📦 Raw Materials":
        show_raw_materials(df_raw, t)
    
    elif selected_page == "🏭 Finished Goods":
        show_finished_goods(df_fg, t)
    
    elif selected_page == "👥 Users":
        if st.session_state.get('user_role') == "admin":
            show_users(t)
        else:
            st.warning("⛔ غير مصرح لك بالدخول لهذه الصفحة")
    
    elif selected_page == "⚙️ Settings":
        if st.session_state.get('user_role') == "admin":
            show_settings(t)
        else:
            st.warning("⛔ غير مصرح لك بالدخول لهذه الصفحة")
    
    # Admin: حذف السجلات
    if st.session_state.get('user_role') == "admin":
        show_delete_records(df_raw, df_fg, t)
    
    # Footer
    st.markdown('<div class="footer">© 2024 BIRMA Integrated System | جميع الحقوق محفوظة</div>', unsafe_allow_html=True)

# ============================================================================
if __name__ == "__main__":
    main()