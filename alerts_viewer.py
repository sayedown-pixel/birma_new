# alerts_viewer.py - استبدل دالة show_alerts_panel بهذه النسخة

import streamlit as st
import pandas as pd
from datetime import datetime
from database import db_manager

def show_alerts_panel(t):
    """عرض لوحة التنبيهات بشكل مخفي مع أيقونة وعداد"""
    
    alerts = db_manager.get_active_alerts(limit=50)
    
    if not alerts:
        return
    
    # حساب عدد التنبيهات حسب الخطورة
    critical_count = len([a for a in alerts if a['severity'] == 'critical'])
    warning_count = len([a for a in alerts if a['severity'] == 'warning'])
    info_count = len([a for a in alerts if a['severity'] == 'info'])
    total_count = len(alerts)
    
    # إنشاء أيقونة مع عداد
    icon = "🔔"
    if critical_count > 0:
        icon = "🔴🔔"
    
    # زر لعرض/إخفاء التنبيهات
    with st.expander(f"{icon} **Alerts** ({total_count} active)", expanded=False):
        
        # عرض ملخص سريع
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Critical", critical_count, delta=None)
        with col2:
            st.metric("🟡 Warning", warning_count, delta=None)
        with col3:
            st.metric("🔵 Info", info_count, delta=None)
        
        st.markdown("---")
        
        # عرض التنبيهات حسب الخطورة
        for alert in alerts:
            with st.container():
                if alert['severity'] == 'critical':
                    st.error(f"**{alert['title']}**")
                elif alert['severity'] == 'warning':
                    st.warning(f"**{alert['title']}**")
                else:
                    st.info(f"**{alert['title']}**")
                
                st.caption(f"📝 {alert['message']}")
                
                col1, col2, col3 = st.columns([4, 1, 1])
                with col2:
                    st.caption(f"📅 {alert['created_at'].strftime('%Y-%m-%d')}")
                with col3:
                    # ✅ استخدام session_state لتتبع حالة الزر
                    button_key = f"dismiss_{alert['id']}_{alert['created_at']}"
                    if st.button("✅ Dismiss", key=button_key, help="Remove this alert"):
                        success = db_manager.dismiss_alert(alert['id'], st.session_state.get('username', ''))
                        if success:
                            st.session_state[f"dismissed_{alert['id']}"] = True
                            st.rerun()
                st.markdown("---")


def show_alerts_page(t):
    """صفحة إدارة التنبيهات الكاملة"""
    st.header("🔔 " + t.get("alerts_title", "Alert Management"))
    
    tab_active, tab_history = st.tabs([
        t.get("alerts_tab_active", "🔔 Active Alerts"),
        t.get("alerts_tab_history", "📜 Alert History")
    ])
    
    with tab_active:
        alerts = db_manager.get_active_alerts()
        
        if not alerts:
            st.info(t.get("alerts_no_active", "✅ No active alerts"))
        else:
            for alert in alerts:
                col1, col2, col3 = st.columns([5, 2, 1])
                with col1:
                    if alert['severity'] == 'critical':
                        st.error(f"**{alert['title']}**")
                    elif alert['severity'] == 'warning':
                        st.warning(f"**{alert['title']}**")
                    else:
                        st.info(f"**{alert['title']}**")
                    st.caption(alert['message'])
                    st.caption(f"📅 {alert['created_at'].strftime('%Y-%m-%d %H:%M')}")
                with col2:
                    st.caption(f"Type: {alert['alert_type']}")
                with col3:
                    button_key = f"dismiss_page_{alert['id']}_{alert['created_at']}"
                    if st.button("✅ Dismiss", key=button_key):
                        success = db_manager.dismiss_alert(alert['id'], st.session_state.get('username', ''))
                        if success:
                            st.rerun()
                st.markdown("---")
    
    with tab_history:
        alerts = db_manager.get_all_alerts(limit=100, include_dismissed=True)
        
        if alerts:
            df = pd.DataFrame(alerts)
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            display_cols = ['created_at', 'alert_type', 'severity', 'title', 'message', 'dismissed_by']
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available_cols], use_container_width=True)
        else:
            st.info(t.get("alerts_no_history", "📭 No alert history"))