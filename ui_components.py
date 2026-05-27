# ui_components.py
import streamlit as st
import time
from datetime import datetime

# ============================================================================
# Loading Indicators
# ============================================================================

@st.dialog("📢 إشعار", width="small")
def show_notification_dialog(title, message, type="info"):
    """عرض إشعار منبثق"""
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    st.markdown(f"### {icons.get(type, 'ℹ️')} {title}")
    st.markdown(message)
    if st.button("حسناً"):
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

def with_loading(message="جاري المعالجة..."):
    """Decorator لعرض مؤشر تحميل أثناء تنفيذ دالة"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with st.spinner(message):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================================
# Enhanced Metrics Cards
# ============================================================================

def metric_card(title, value, delta=None, delta_color="normal", icon=None):
    """بطاقة متقدمة للقياسات - نسخة مبسطة"""
    icons = {
        "production": "🏭", "efficiency": "⚡", "downtime": "⏰", 
        "quality": "✅", "stock": "📦", "users": "👥", "money": "💰",
        "oee": "📊", "maintenance": "🔧", "delivery": "🚚"
    }
    icon_display = icons.get(icon, "📊") if icon else "📊"
    
    # عرض باستخدام st.metric العادية
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"<span style='font-size:1.5rem;'>{icon_display}</span>", unsafe_allow_html=True)
    with col2:
        if delta:
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
    user_name = st.session_state.get('user_name', 'زائر')
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

def date_range_picker(label="اختر الفترة"):
    """مكون لاختيار نطاق زمني متقدم"""
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        start_date = st.date_input("من تاريخ", datetime.now().date())
    with col2:
        st.markdown("<div style='text-align:center; margin-top:25px;'>→</div>", unsafe_allow_html=True)
    with col3:
        end_date = st.date_input("إلى تاريخ", datetime.now().date())
    
    # Preset options
    preset = st.selectbox(label, ["آخر 7 أيام", "آخر 30 يوم", "آخر 90 يوم", "هذا الشهر", "الشهر الماضي", "تخصيص"])
    
    if preset == "آخر 7 أيام":
        from datetime import timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
    elif preset == "آخر 30 يوم":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    elif preset == "آخر 90 يوم":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
    
    return start_date, end_date

# ============================================================================
# Export Buttons
# ============================================================================

def export_buttons(data, filename="export", formats=["Excel", "CSV", "PDF"]):
    """أزرار تصدير البيانات"""
    st.markdown("### 📤 تصدير البيانات")
    
    cols = st.columns(len(formats))
    for i, fmt in enumerate(formats):
        with cols[i]:
            if fmt == "Excel":
                if st.button("📊 Excel", use_container_width=True):
                    data.to_excel(f"{filename}.xlsx", index=False)
                    st.success(f"✅ تم التصدير إلى {filename}.xlsx")
            elif fmt == "CSV":
                if st.button("📄 CSV", use_container_width=True):
                    data.to_csv(f"{filename}.csv", index=False, encoding='utf-8-sig')
                    st.success(f"✅ تم التصدير إلى {filename}.csv")
            elif fmt == "PDF":
                if st.button("📑 PDF", use_container_width=True):
                    st.info("🔧 يتم إنشاء ملف PDF...")

# ============================================================================
# Confirm Dialog
# ============================================================================

@st.dialog("⚠️ تأكيد العملية", width="small")
def confirm_dialog(message, on_confirm):
    """نافذة تأكيد قبل تنفيذ عملية مهمة"""
    st.warning(message)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("نعم, متأكد", type="primary", use_container_width=True):
            on_confirm()
            st.rerun()
    with col2:
        if st.button("إلغاء", use_container_width=True):
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