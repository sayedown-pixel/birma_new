# alerts_viewer.py - استبدل دالة show_alerts_panel بالكامل

import streamlit as st
from database import db_manager
from datetime import datetime


def show_alerts_panel(t):
    """عرض لوحة التنبيهات الجانبية - مع دعم كامل للغة"""
    
    lang = st.session_state.get('lang', 'ar')
    
    # ✅ عنوان منسق
    st.sidebar.markdown("---")
    st.sidebar.subheader(t.get("alert_title", "🔔 Alerts"))
    
    try:
        alerts = db_manager.get_active_alerts(limit=10)
    except Exception as e:
        st.sidebar.error(f"Error loading alerts: {e}")
        return
    
    if not alerts:
        st.sidebar.info(t.get("no_active_alerts", "✅ No active alerts"))
        return
    
    # عرض التنبيهات حسب الخطورة
    for alert in alerts:
        severity = alert.get('severity', 'warning')
        title = alert.get('title', '')
        message = alert.get('message', '')
        created_at = alert.get('created_at')
        
        # ✅ إزالة الرموز المكررة من العنوان
        # تنظيف العنوان من الرموز المكررة
        clean_title = title
        if clean_title.startswith("🟡 🟡"):
            clean_title = clean_title.replace("🟡 🟡", "🟡")
        if clean_title.startswith("🔴 🔴"):
            clean_title = clean_title.replace("🔴 🔴", "🔴")
        
        # تنسيق الوقت
        time_str = ""
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except:
                    pass
            if hasattr(created_at, 'strftime'):
                if lang == 'ar':
                    time_str = f"🕐 {created_at.strftime('%H:%M')}"
                else:
                    time_str = f"🕐 {created_at.strftime('%H:%M')}"
        
        # عرض التنبيه حسب الخطورة
        if severity == 'critical':
            st.sidebar.error(f"""
🔴 **{clean_title}**
{message}
{time_str}
""")
        elif severity == 'warning':
            st.sidebar.warning(f"""
🟡 **{clean_title}**
{message}
{time_str}
""")
        else:
            st.sidebar.info(f"""
🔵 **{clean_title}**
{message}
{time_str}
""")
        
        # زر تأكيد وإزالة التنبيه (للمسؤول فقط)
        if st.session_state.get('user_role') == 'admin':
            col1, col2 = st.sidebar.columns([3, 1])
            with col2:
                if st.button("✓", key=f"dismiss_alert_{alert.get('id')}", help=t.get("confirm_label", "Confirm")):
                    try:
                        db_manager.dismiss_alert(alert.get('id'), st.session_state.get('user_name', 'admin'))
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error: {e}")
        
        st.sidebar.markdown("---")


def show_alerts_page(t):
    """صفحة كاملة لعرض وإدارة التنبيهات"""
    
    st.header(t.get("alerts_title", "🔔 Alert Management"))
    
    tab1, tab2 = st.tabs([
        t.get("alerts_tab_active", "🔔 Active Alerts"),
        t.get("alerts_tab_history", "📜 Alert History")
    ])
    
    with tab1:
        st.subheader(t.get("alerts_tab_active", "🔔 Active Alerts"))
        
        try:
            alerts = db_manager.get_active_alerts(limit=50)
            
            if not alerts:
                st.info(t.get("alerts_no_active", "✅ No active alerts"))
            else:
                for alert in alerts:
                    severity = alert.get('severity', 'warning')
                    title = alert.get('title', '')
                    message = alert.get('message', '')
                    created_at = alert.get('created_at')
                    
                    # ✅ تنظيف العنوان من الرموز المكررة
                    clean_title = title
                    if clean_title.startswith("🟡 🟡"):
                        clean_title = clean_title.replace("🟡 🟡", "🟡")
                    if clean_title.startswith("🔴 🔴"):
                        clean_title = clean_title.replace("🔴 🔴", "🔴")
                    if clean_title.startswith("🚨"):
                        clean_title = clean_title
                    
                    if severity == 'critical':
                        with st.expander(f"🔴 {clean_title}", expanded=True):
                            st.error(message)
                            if created_at:
                                st.caption(f"📅 {created_at}")
                            col1, col2 = st.columns([3, 1])
                            with col2:
                                if st.button("✓ " + t.get("confirm_label", "Confirm"), key=f"dismiss_{alert.get('id')}"):
                                    db_manager.dismiss_alert(alert.get('id'), st.session_state.get('user_name', 'admin'))
                                    st.rerun()
                    elif severity == 'warning':
                        with st.expander(f"🟡 {clean_title}"):
                            st.warning(message)
                            if created_at:
                                st.caption(f"📅 {created_at}")
                            col1, col2 = st.columns([3, 1])
                            with col2:
                                if st.button("✓ " + t.get("confirm_label", "Confirm"), key=f"dismiss_{alert.get('id')}"):
                                    db_manager.dismiss_alert(alert.get('id'), st.session_state.get('user_name', 'admin'))
                                    st.rerun()
                    else:
                        with st.expander(f"🔵 {clean_title}"):
                            st.info(message)
                            if created_at:
                                st.caption(f"📅 {created_at}")
                            col1, col2 = st.columns([3, 1])
                            with col2:
                                if st.button("✓ " + t.get("confirm_label", "Confirm"), key=f"dismiss_{alert.get('id')}"):
                                    db_manager.dismiss_alert(alert.get('id'), st.session_state.get('user_name', 'admin'))
                                    st.rerun()
        except Exception as e:
            st.error(f"Error loading alerts: {e}")
    
    with tab2:
        st.subheader(t.get("alerts_tab_history", "📜 Alert History"))
        
        try:
            dismissed_alerts = db_manager.get_all_alerts(limit=100, include_dismissed=True)
            
            if not dismissed_alerts:
                st.info(t.get("alerts_no_history", "📭 No alert history"))
            else:
                dismissed = [a for a in dismissed_alerts if a.get('is_dismissed', False)]
                
                if not dismissed:
                    st.info(t.get("alerts_no_history", "📭 No alert history"))
                else:
                    for alert in dismissed[:50]:
                        severity = alert.get('severity', 'warning')
                        title = alert.get('title', '')
                        message = alert.get('message', '')
                        created_at = alert.get('created_at')
                        dismissed_at = alert.get('dismissed_at')
                        dismissed_by = alert.get('dismissed_by')
                        
                        # تنظيف العنوان
                        clean_title = title
                        if clean_title.startswith("🟡 🟡"):
                            clean_title = clean_title.replace("🟡 🟡", "🟡")
                        if clean_title.startswith("🔴 🔴"):
                            clean_title = clean_title.replace("🔴 🔴", "🔴")
                        
                        if severity == 'critical':
                            icon = "🔴"
                        elif severity == 'warning':
                            icon = "🟡"
                        else:
                            icon = "🔵"
                        
                        with st.expander(f"{icon} {clean_title}"):
                            st.write(message)
                            col1, col2 = st.columns(2)
                            with col1:
                                st.caption(f"📅 Created: {created_at}")
                            with col2:
                                st.caption(f"✓ Dismissed: {dismissed_at} by {dismissed_by}")
        except Exception as e:
            st.error(f"Error loading alert history: {e}")