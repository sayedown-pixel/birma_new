# ui_components.py
import streamlit as st
import time
from datetime import datetime

# ============================================================================
# Lazy translation helper for module-level use (decorators)
# ============================================================================

class _LazyT:
    """Lazy translation helper - falls back to default if t not in session state."""
    def get(self, key, default=None):
        try:
            if 't' in st.session_state:
                return st.session_state.t.get(key, default)
        except Exception:
            pass
        return default

_lt = _LazyT()

def _load_t():
    from helpers import load_language
    lang = st.session_state.get('lang', 'ar')
    return load_language(lang)

# ============================================================================
# نظام ألوان موحد - أضف هذا في بداية ملف ui_components.py
# ============================================================================

COLORS = {
    "primary": "#1e3a5f",
    "primary_dark": "#0f2b4a",
    "primary_light": "#2c5282",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#3b82f6",
    "dark": "#1e293b",
    "light": "#f8fafc",
    "gray": "#64748b",
    "white": "#ffffff",
}


def apply_unified_theme():
    """تطبيق المظهر الموحد على التطبيق"""
    
    st.markdown(f"""
    <style>
        /* الألوان الأساسية */
        :root {{
            --primary: {COLORS['primary']};
            --primary-dark: {COLORS['primary_dark']};
            --primary-light: {COLORS['primary_light']};
            --success: {COLORS['success']};
            --warning: {COLORS['warning']};
            --danger: {COLORS['danger']};
            --info: {COLORS['info']};
            --dark: {COLORS['dark']};
            --light: {COLORS['light']};
            --gray: {COLORS['gray']};
        }}
        
        /* تنسيق البطاقات */
        div[data-testid="stMetric"] {{
            background: white;
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }}
        
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        /* تنسيق الأزرار */
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        
        /* تنسيق التبويبات */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0;
            padding: 8px 16px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: var(--primary) !important;
            color: white !important;
        }}
        
        /* شريط جانبي */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%) !important;
        }}
        
        /* تنسيق رسائل النجاح/الخطأ */
        .stAlert {{
            border-radius: 8px !important;
            border-right: 4px solid !important;
        }}
        
        .stAlert[data-baseweb="notification"] {{
            border-right-color: var(--success) !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def show_marquee_items(items):
    """عرض شريط متحرك للتوصيات"""
    if not items:
        return
    
    html_items = []
    for item in items:
        if "🔴" in item:
            bg = COLORS['danger']
        elif "🟡" in item:
            bg = COLORS['warning']
        else:
            bg = COLORS['success']
        
        html_items.append(f'<span style="background:{bg};color:white;padding:8px 20px;border-radius:40px;margin:0 10px;display:inline-block;font-size:14px;font-weight:bold;white-space:nowrap;">{item}</span>')
    
    all_items = "".join(html_items) + "".join(html_items)
    
    st.markdown(f'''
    <div style="background:{COLORS['primary']};border-radius:50px;padding:12px 0;margin:15px 0;overflow:hidden;">
        <div style="display:inline-block;white-space:nowrap;animation:scrollLine 25s linear infinite;">
            {all_items}
        </div>
    </div>
    <style>
        @keyframes scrollLine {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-50%); }}
        }}
    </style>
    ''', unsafe_allow_html=True)
@st.dialog(_lt.get("notification", "📢 Notification"), width="small")
def show_notification_dialog(title, message, type="info"):
    """عرض إشعار منبثق"""
    t = _load_t()
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    st.markdown(f"### {icons.get(type, 'ℹ️')} {title}")
    st.markdown(message)
    if st.button(t.get("ok_label", "OK")):
        st.rerun()

def show_toast(message, type="info", duration=3):
    """عرض إشعار مؤقت (Toast)"""
    colors = {
        "success": "#10b981",
        "error": "#ef4444", 
        "warning": "#f59e0b",
        "info": "#3b82f6"
    }
    icons = {"success": "✓", "error": "✗", "warning": "⚠", "info": "ℹ"}
    
    toast_html = f"""
    <div style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: {colors.get(type, '#3b82f6')};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        font-weight: 500;
        animation: slideIn 0.3s ease;
    ">
        {icons.get(type, 'ℹ')} {message}
    </div>
    <style>
        @keyframes slideIn {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
    </style>
    """
    st.markdown(toast_html, unsafe_allow_html=True)
    time.sleep(duration)

def with_loading(message=None):
    """Decorator لعرض مؤشر تحميل أثناء تنفيذ دالة"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            t = _load_t()
            msg = message if message is not None else t.get("processing", "Processing...")
            with st.spinner(msg):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================================
# Enhanced Metrics Cards
# ============================================================================

# ui_components.py - استبدل دالة metric_card بهذه النسخة

def metric_card(title, value, delta=None, delta_color="normal", icon=None):
    """
    بطاقة متقدمة للقياسات - نسخة مبسطة ونظيفة
    """
    icons = {
        "production": "🏭", "efficiency": "⚡", "downtime": "⏰", 
        "quality": "✅", "stock": "📦", "users": "👥", "money": "💰",
        "oee": "📊", "maintenance": "🔧", "delivery": "🚚"
    }
    icon_display = icons.get(icon, "📊") if icon else "📊"
    
    # ✅ استخدام st.metric العادية فقط - بدون HTML معقد
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"<span style='font-size:1.5rem;'>{icon_display}</span>", unsafe_allow_html=True)
    with col2:
        if delta is not None:
            st.metric(title, f"{value:,}" if isinstance(value, (int, float)) else value, delta=f"{delta:.1f}%")
        else:
            st.metric(title, f"{value:,}" if isinstance(value, (int, float)) else value)
# ============================================================================
# Breadcrumbs Navigation
# ============================================================================

def show_breadcrumbs(pages):
    """عرض مسار التنقل (Breadcrumbs)"""
    breadcrumb_html = '<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;">'
    
    for i, page in enumerate(pages):
        if i == len(pages) - 1:
            breadcrumb_html += f'<span style="color: #94a3b8;">{page}</span>'
        else:
            breadcrumb_html += f'<span style="color: #3b82f6;">{page}</span>'
            breadcrumb_html += '<span style="color: #64748b;">›</span>'
    
    breadcrumb_html += '</div>'
    st.markdown(breadcrumb_html, unsafe_allow_html=True)

# ============================================================================
# Enhanced Sidebar
# ============================================================================

def show_user_profile():
    """عرض ملف المستخدم في الشريط الجانبي"""
    user_name = st.session_state.get('user_name', 'Visitor')
    user_role = st.session_state.get('user_role', '')
    user_email = st.session_state.get('user_email', '')
    
    role_icons = {
        "admin": "👑", "supervisor": "👔", 
        "technician": "🔧", "storekeeper": "📦", "quality": "🔍"
    }
    role_icon = role_icons.get(user_role, "👤")
    
    profile_html = f"""
    <div style="
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
    ">
        <div style="font-size: 3rem;">{role_icon}</div>
        <div style="font-weight: bold; color: white; margin-top: 5px;">{user_name}</div>
        <div style="font-size: 0.75rem; color: #94a3b8;">{user_role}</div>
        <div style="font-size: 0.7rem; color: #64748b; margin-top: 5px;">{user_email}</div>
    </div>
    """
    st.markdown(profile_html, unsafe_allow_html=True)

# ============================================================================
# Date Range Picker
# ============================================================================

def date_range_picker(label=None):
    """مكون لاختيار نطاق زمني متقدم"""
    t = _load_t()
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        start_date = st.date_input(t.get("from_date", "From date"), datetime.now().date())
    with col2:
        st.markdown("<div style='text-align:center; margin-top:25px;'>→</div>", unsafe_allow_html=True)
    with col3:
        end_date = st.date_input(t.get("to_date", "To date"), datetime.now().date())
    
    # Preset options
    preset_options = [
        t.get("last_7_days", "آخر 7 أيام"),
        t.get("last_30_days", "آخر 30 يوم"),
        t.get("last_90_days", "آخر 90 يوم"),
        t.get("this_month", "هذا الشهر"),
        t.get("last_month", "الشهر الماضي"),
        t.get("custom", "تخصيص"),
    ]
    preset_label = label if label is not None else t.get("select_period", "Select Period")
    preset = st.selectbox(preset_label, preset_options)
    
    if preset == preset_options[0]:
        from datetime import timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
    elif preset == preset_options[1]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    elif preset == preset_options[2]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
    
    return start_date, end_date

# ============================================================================
# Export Buttons
# ============================================================================

def export_buttons(data, filename="export", formats=["Excel", "CSV", "PDF"]):
    """أزرار تصدير البيانات"""
    t = _load_t()
    st.markdown(t.get("export_data", "### 📤 Export Data"))
    
    cols = st.columns(len(formats))
    for i, fmt in enumerate(formats):
        with cols[i]:
            if fmt == "Excel":
                if st.button("📊 Excel", width='stretch'):
                    data.to_excel(f"{filename}.xlsx", index=False)
                    st.success(t.get("exported_excel", "✅ Exported to {filename}.xlsx").format(filename=filename))
            elif fmt == "CSV":
                if st.button("📄 CSV", width='stretch'):
                    data.to_csv(f"{filename}.csv", index=False, encoding='utf-8-sig')
                    st.success(t.get("exported_csv", "✅ Exported to {filename}.csv").format(filename=filename))
            elif fmt == "PDF":
                if st.button("📑 PDF", width='stretch'):
                    st.info(t.get("generating_pdf", "🔧 Generating PDF..."))

# ============================================================================
# Confirm Dialog
# ============================================================================

@st.dialog(_lt.get("confirm_action", "⚠️ Confirm Action"), width="small")
def confirm_dialog(message, on_confirm):
    """نافذة تأكيد قبل تنفيذ عملية مهمة"""
    t = _load_t()
    st.warning(message)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t.get("yes_confirm", "Yes, Confirm"), type="primary", width='stretch'):
            on_confirm()
            st.rerun()
    with col2:
        if st.button(t.get("cancel", "Cancel"), width='stretch'):
            st.rerun()

# ============================================================================
# Progress Tracker
# ============================================================================

def progress_tracker(steps, current_step):
    """عرض متتبع التقدم (Stepper)"""
    html = '<div style="display: flex; justify-content: space-between; margin: 20px 0;">'
    
    for i, step in enumerate(steps):
        is_active = i <= current_step
        is_current = i == current_step
        
        if is_current:
            bg = "#3b82f6"
            color = "white"
        elif is_active:
            bg = "#10b981"
            color = "white"
        else:
            bg = "#e2e8f0"
            color = "#94a3b8"
        
        html += f"""
        <div style="text-align: center; flex: 1;">
            <div style="
                width: 30px;
                height: 30px;
                background: {bg};
                color: {color};
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 5px auto;
                font-weight: bold;
            ">{i+1}</div>
            <div style="font-size: 0.7rem; color: {color if is_current else '#64748b'};">{step}</div>
        </div>
        """
        if i < len(steps) - 1:
            html += f'<div style="flex: 1; height: 2px; background: {bg if is_active else "#e2e8f0"}; margin-top: 15px;"></div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)