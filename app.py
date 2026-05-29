import streamlit as st
import pandas as pd
from datetime import datetime
import os
# أضف في بداية app.py مع الاستيرادات الأخرى
from ui_components import show_user_profile, show_breadcrumbs, show_toast, with_loading, metric_card
from inventory_db import get_raw_materials_df, get_finished_goods_df
from auth import init_session_state, login_screen, logout
from database import db_manager
from utils import load_language, LANG, ROLE_PERMISSIONS, USERS
from dashboard import show_dashboard
from production import show_production
from maintenance import show_maintenance
from records import show_records
from helpers import clean_line_name
from inventory import (
    show_raw_materials, show_finished_goods,
    load_raw_materials, load_finished_goods,
    register_inventory_cache_invalidator,
)
from admin import show_users, show_settings, show_delete_records
from oee_analytics import show_oee_dashboard
from inventory_db import get_raw_materials_df, get_finished_goods_df
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
def clean_line_display(line):
    if not line:
        return ""
    if "الخط الأول" in line or "line 1" in line.lower():
        return "Line 1"
    elif "الخط الثاني" in line or "line 2" in line.lower():
        return "Line 2"
    return line

    # ✅ اسم الخط المعروض (للطباعة أو العرض)
    line_display = clean_line_display(selected_line)

# ============================================================================
# Page configuration
# ============================================================================
st.set_page_config(
    page_title="Smart Factory System",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ============================================================================
# Force Sidebar Dark Mode - حل جذري للمشكلة
# ============================================================================

st.markdown("""
<style>
    /* قوة قصوى لتصحيح السايدبار */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"],
    [data-testid="stSidebar"] .st-emotion-cache-1y4p8pa,
    [data-testid="stSidebar"] .st-emotion-cache-6qob1r,
    [data-testid="stSidebar"] .st-emotion-cache-10trblm,
    [data-testid="stSidebar"] .st-emotion-cache-1v0mbdj,
    [data-testid="stSidebar"] .st-emotion-cache-1wmy9hl {
        background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%) !important;
        background-color: #0f172a !important;
    }
    
    /* جميع النصوص في السايدبار */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stRadio label p,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSelectbox div,
    [data-testid="stSidebar"] .stSelectbox span,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption p {
        color: #ffffff !important;
    }
    
    /* عناصر القائمة */
    [data-testid="stSidebar"] .stRadio label {
        background: rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
        margin: 2px 0 !important;
    }
    
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.2) !important;
    }
    
    /* الأزرار */
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.15) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    
    /* الفواصل */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2) !important;
    }
    
    /* الروابط */
    [data-testid="stSidebar"] a {
        color: #93c5fd !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Custom CSS
# ============================================================================

def apply_custom_css():
    st.markdown("""
    <style>
    /* قوة قصوى للسايدبار - داكن */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        background: #0f172a !important;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stRadio label {
        background: #1e293b !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #334155 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox div {
        background: #1e293b !important;
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: #1e293b !important;
        color: white !important;
        border: none !important;
    }
    
    /* البطاقات */
    div[data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    div[data-testid="stMetric"] label {
        color: #64748b !important;
    }
    
    div[data-testid="stMetric"] div {
        color: #1e293b !important;
    }
    
    /* الهيدر */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        padding: 1rem 2rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .logo-icon {
        font-size: 2rem;
    }
    
    .company-title h1 {
        margin: 0;
        font-size: 1.3rem;
        color: white;
    }
    
    .company-title p {
        margin: 0;
        font-size: 0.7rem;
        color: #cbd5e1;
    }
    
    .user-section {
        text-align: right;
        color: white;
    }
    
    .footer {
        text-align: center;
        padding: 1rem;
        margin-top: 2rem;
        color: #94a3b8;
        font-size: 0.8rem;
        border-top: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)
     # في app.py، بعد db_manager initialization، أضف:

# تشغيل النسخ الاحتياطي التلقائي (مرة واحدة يومياً)
    try:
        from backup_manager import run_auto_backup
        run_auto_backup()
    except Exception as e:
        pass  # لا نعرض خطأ للمستخدم
# ============================================================================
# Sidebar navigation
# ============================================================================

# app.py - قم بتحديث دالة show_sidebar فقط

# app.py - استبدل دالة show_sidebar بهذه النسخة

# app.py - دالة show_sidebar كاملة

def show_sidebar(t):
    """بناء القائمة الجانبية"""
    role = st.session_state.get('user_role', 'supervisor')
    allowed_pages = ROLE_PERMISSIONS.get(role, [])

    with st.sidebar:
        # تحسين عرض النصوص في السايدبار
        show_user_profile()
        
        # شعار صغير في السايدبار
        st.markdown(f"""
        <div style="text-align: center; padding: 10px 0;">
            <span style="font-size: 3rem;">🏭</span>
            <h3 style="color: white; margin: 0;">{t.get('app_title', 'Smart Factory')}</h3>
            <p style="color: #a0aec0; font-size: 0.7rem;">{t.get('system_subtitle', 'Integrated System')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # اختيار اللغة والوضع
        col_l, col_d = st.columns(2)
        with col_l:
            current_lang = st.session_state.get('lang', 'ar')
            if current_lang == 'ar':
                if st.button("🇬🇧 " + t.get("english_btn", "English"), width='stretch'):
                    st.session_state.lang = 'en'
                    st.session_state.t = load_language('en')
                    st.rerun()
            else:
                if st.button("🇸🇦 " + t.get("arabic_btn", "عربي"), width='stretch'):
                    st.session_state.lang = 'ar'
                    st.session_state.t = load_language('ar')
                    st.rerun()
        
        with col_d:
            dark = st.session_state.get('dark_mode', False)
            dark_label = "🌙" if not dark else "☀️"
            if st.button(dark_label, width='stretch'):
                st.session_state.dark_mode = not dark
        
        st.markdown("---")
        
        # قائمة الصفحات
        page_mapping = {
            "🏠 Dashboard": t.get("dashboard", "🏠 Dashboard"),
            "📈 Production": t.get("production", "📈 Production"),
            "🔧 Maintenance": t.get("maintenance", "🔧 Maintenance"),
            "📊 Records": t.get("records", "📊 Records"),
            "📦 Raw Materials": t.get("raw_materials", "📦 Raw Materials"),
            "🏭 Finished Goods": t.get("finished_goods", "🏭 Finished Goods"),
            "👥 Users": t.get("users", "👥 Users"),
            "⚙️ Settings": t.get("settings", "⚙️ Settings"),
            "🔔 Alerts": t.get("alerts_title", "🔔 Alerts"), 
        }
        
        # إضافة صفحة السجلات للمسؤول فقط
        if role == "admin":
            page_mapping["📋 System Logs"] = t.get("logs_title", "📋 System Logs")
        
        # إنشاء قائمة الخيارات المعروضة
        page_options = []
        page_keys = []
        for page_key in page_mapping.keys():
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
        
        # اختيار خط الإنتاج - ✅ مبسط بدون دوال خارجية
        selected_line = None
        if selected_page in ["📈 Production", "🔧 Maintenance", "🏠 Dashboard"]:
            st.markdown("---")
            # ✅ استخدام Line 1 و Line 2 مباشرة
            line_options = ["Line 1", "Line 2"]
            selected_line = st.selectbox(
                t.get("line_label", "خط الإنتاج"),
                line_options,
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
        
        st.caption(f"© {datetime.now().year} {t.get('app_title', 'Smart Factory System')}")
    
    return selected_page, selected_line

@st.cache_data(show_spinner=False)
def _load_inventory_cached(inventory_version: int):
    """تحميل المخزون من قاعدة البيانات"""
    return get_raw_materials_df(), get_finished_goods_df()

def load_inventory_data():
    version = st.session_state.get("inventory_version", 0)
    return _load_inventory_cached(version)
if hasattr(_load_inventory_cached, 'clear'):
    register_inventory_cache_invalidator(_load_inventory_cached.clear)
else:
    register_inventory_cache_invalidator(lambda: None)

# ============================================================================
# Main application
# ============================================================================

def main():
    # تطبيق التنسيقات
    apply_custom_css()
    
    # تهيئة الجلسة أولاً
    init_session_state()
    
    # تحميل اللغة مبكراً (قبل أي استخدام لـ t)
    lang = st.session_state.get('lang', 'ar')
    t = load_language(lang)
    
    # التحقق من اتصال قاعدة البيانات (بعد تحميل t)
    if not db_manager.is_connected():
        st.error(f"{t.get('db_connection_error', '❌ Database connection failed')}: {db_manager.get_init_error()}")
        st.info(t.get("db_sqlite_fallback", "Using SQLite as local database. smart_factory.db will be created automatically."))
    
    # شاشة تسجيل الدخول
    if not st.session_state.get('authenticated', False):
        login_screen(t)
        return
    
    # التحقق من تغيير كلمة المرور الإجباري
    # if st.session_state.get('must_change_password', False):
    #     from auth import force_change_password_screen
    #    force_change_password_screen()
     #   return
    
    # تحميل بيانات المخزون
    df_raw, df_fg = load_inventory_data()
    
    if df_raw is None or df_raw.empty:
        st.sidebar.warning(t.get("raw_file_missing", "⚠️ Raw materials file not found or empty"))
        df_raw = pd.DataFrame()
    
    if df_fg is None or df_fg.empty:
        st.sidebar.warning(t.get("fg_file_missing", "⚠️ Finished goods file not found or empty"))
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
                <h1>{t.get('app_title', 'Smart Factory System')}</h1>
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
        if st.button("🚪 " + t.get('logout_btn', 'خروج'), width='stretch'):
            logout()
    
    # ======================================================================
    # Sidebar and Navigation
    # ======================================================================
    selected_page, selected_line = show_sidebar(t)
    if not selected_line:
        selected_line = "(line 1)"    
    if not selected_line:
        selected_line = "(line 1)"
        
    
    # تحميل بيانات الإنتاج للصفحات التي تحتاجها
    df_main = pd.DataFrame()
    if selected_page in ["🏠 Dashboard", "📈 Production", "🔧 Maintenance"]:
        try:
            df_main = db_manager.get_all_production()
        except Exception as e:
            st.warning(f"{t.get('loading_error', 'Failed to load production data')}: {e}")
    
    # ======================================================================
    # Page Routing
    # ======================================================================
    
    if selected_page == "🏠 Dashboard":
        show_dashboard(df_main, df_raw, df_fg, t, selected_line)
    elif selected_page == "🔔 Alerts":
        if st.session_state.get('user_role') == "admin":
            from alerts_viewer import show_alerts_page
            show_alerts_page(t)
        else:
            st.warning(t.get("unauthorized", "⛔ Unauthorized access"))    
    
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
            st.warning(t.get("unauthorized", "⛔ Unauthorized access"))
    
    elif selected_page == "⚙️ Settings":
        if st.session_state.get('user_role') == "admin":
            show_settings(t)
        else:
            st.warning(t.get("unauthorized", "⛔ Unauthorized access"))
    elif selected_page == "📋 System Logs":
        if st.session_state.get('user_role') == "admin":
            from logs_viewer import show_logs_viewer
            show_logs_viewer(t)
        else:
            st.warning(t.get("unauthorized", "⛔ Unauthorized access"))        
    
    # Admin: حذف السجلات
    if st.session_state.get('user_role') == "admin":
        show_delete_records(df_raw, df_fg, t)
    
    # Footer
    st.markdown(f'<div class="footer">{t.get("footer_text", "© 2024 Smart Factory System | All Rights Reserved")}</div>', unsafe_allow_html=True)
if __name__ == "__main__":
    main()
# أضف هذه الدوال في نهاية ملف inventory_db.py

def update_raw_material_stock_db(material_name, quantity, transaction_type, reference='', notes='', created_by=''):
    """تحديث مخزون مادة خام (وارد/صرف)"""
    session = db_manager.get_session()
    try:
        from database import RawMaterial, RawMaterialTransaction
        
        # البحث عن المادة بالاسم العربي أو الإنجليزي
        material = session.query(RawMaterial).filter(
            (RawMaterial.name_ar == material_name) | 
            (RawMaterial.name_en == material_name)
        ).first()
        
        if not material:
            return False, f"❌ المادة '{material_name}' غير موجودة"
        
        if transaction_type == 'receipt':
            material.current_stock += quantity
        elif transaction_type == 'consumption':
            if material.current_stock < quantity:
                return False, f"❌ رصيد غير كافٍ للمادة '{material_name}': المتوفر {material.current_stock}"
            material.current_stock -= quantity
        elif transaction_type == 'adjustment':
            material.current_stock = quantity
        
        material.last_updated = datetime.now()
        
        # تسجيل الحركة
        transaction = RawMaterialTransaction(
            material_id=material.id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            created_by=created_by,
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        return True, f"✅ تم تحديث مخزون '{material_name}': الرصيد الجديد {material.current_stock}"
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        session.close()


def update_finished_good_stock_db(product_name, quantity, transaction_type, reference='', customer='', notes='', created_by=''):
    """تحديث مخزون منتج تام (إنتاج/تسليم)"""
    session = db_manager.get_session()
    try:
        from database import FinishedGood, FinishedGoodTransaction
        
        # البحث عن المنتج بالاسم
        good = session.query(FinishedGood).filter(FinishedGood.name == product_name).first()
        
        if not good:
            return False, f"❌ المنتج '{product_name}' غير موجود"
        
        if transaction_type == 'production':
            good.stock_in += quantity
            good.balance += quantity
        elif transaction_type == 'delivery':
            if good.balance < quantity:
                return False, f"❌ رصيد غير كافٍ للمنتج '{product_name}': المتوفر {good.balance}"
            good.stock_out += quantity
            good.balance -= quantity
        elif transaction_type == 'adjustment':
            good.balance = quantity
        
        good.last_updated = datetime.now()
        
        # تسجيل الحركة
        transaction = FinishedGoodTransaction(
            finished_good_id=good.id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference=reference,
            customer=customer,
            notes=notes,
            created_by=created_by,
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        return True, f"✅ تم تحديث مخزون '{product_name}': الرصيد الجديد {good.balance}"
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        session.close()


def add_to_finished_goods_db(product_name, quantity, line):
    """إضافة منتج تام إلى المخزون (عند تسجيل إنتاج)"""
    # تحويل اسم المنتج إلى الاسم المستخدم في قاعدة البيانات
    name_mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink": "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    db_name = name_mapping.get(product_name, product_name)
    
    return update_finished_good_stock_db(
        db_name, quantity, 'production',
        reference=f"Production from {line}",
        notes=f"إنتاج {quantity} وحدة من {product_name}",
        created_by=line
    )


def restore_materials_to_db(product, quantity, line):
    """إعادة المواد الخام إلى المخزون (عند حذف سجل إنتاج)"""
    from helpers import get_materials_required, find_raw_materials
    from database import db_manager
    from database import RawMaterial, RawMaterialTransaction
    from datetime import datetime
    
    required, error = get_materials_required(product, quantity)
    if error:
        return False, error
    
    session = None
    try:
        session = db_manager.get_session()
        restored = []
        
        for material_name, req_qty in required.items():
            materials = find_raw_materials(session, material_name)
            if not materials:
                session.rollback()
                return False, f"❌ لم يتم العثور على المادة الخام: {material_name}"
            
            remaining = req_qty
            for material in materials:
                add_qty = min(remaining, req_qty)
                material.current_stock += add_qty
                material.last_updated = datetime.now()
                remaining -= add_qty
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='adjustment',
                    quantity=add_qty,
                    reference=f"Restore from deleted production: {product}",
                    notes=f"استعادة بعد حذف سجل إنتاج - الخط: {line}",
                    created_by="system",
                    created_at=datetime.now()
                )
                session.add(transaction)
                restored.append(f"{material_name}: +{add_qty:,.0f}")
                if remaining <= 0:
                    break
        
        session.commit()
        return True, f"✅ تم إعادة: {', '.join(restored)}"
        
    except Exception as e:
        if session:
            session.rollback()
        return False, f"❌ خطأ في restore_materials_to_db: {str(e)}"
    finally:
        if session:
            session.close()


def restore_finished_goods_from_production_db(product_name, quantity, line):
    """إرجاع منتج تام من المخزون (عند حذف سجل إنتاج) - نخصم من المنتج التام"""
    name_mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink": "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    db_name = name_mapping.get(product_name, product_name)
    
    session = None
    try:
        session = db_manager.get_session()
        from database import FinishedGood, FinishedGoodTransaction
        from datetime import datetime
        
        good = session.query(FinishedGood).filter(FinishedGood.name == db_name).first()
        
        if not good:
            return False, f"❌ المنتج '{product_name}' غير موجود"
        
        print(f"🔍 استرجاع (خصم) المنتج: {db_name}")
        print(f"   المخزون الحالي: {good.balance}")
        print(f"   الكمية المراد خصمها: {quantity}")
        
        # ✅ تصحيح: نخصم الكمية (ننقص من المنتج التام)
        new_balance = good.balance - quantity
        
        # ✅ إذا كان الرصيد سيصبح سالباً، نضعه صفر
        if new_balance < 0:
            print(f"   ⚠️ تحذير: الرصيد سيصبح سالباً ({new_balance})، سيتم تعيينه إلى 0")
            new_balance = 0
        
        good.balance = new_balance
        good.stock_in -= quantity  # نخصم من الوارد
        good.last_updated = datetime.now()
        
        print(f"   المخزون الجديد: {good.balance}")
        
        transaction = FinishedGoodTransaction(
            finished_good_id=good.id,
            transaction_type='adjustment',
            quantity=-quantity,  # كمية سالبة للتسجيل
            reference=f"Restore from deleted production",
            notes=f"حذف إنتاج {quantity} وحدة - الخط: {line}",
            created_by="system",
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        return True, f"✅ تم خصم {quantity} وحدة من {db_name}"
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        if session:
            session.close()
    


def get_raw_materials_list_for_display(lang='ar'):
    """الحصول على قائمة المواد الخام للعرض (مع ترجمة الأسماء)"""
    materials = db_manager.get_all_raw_materials()
    if not materials:
        return []
    
    if lang == 'ar':
        return [m['name_ar'] for m in materials]
    else:
        return [m['name_en'] for m in materials]    