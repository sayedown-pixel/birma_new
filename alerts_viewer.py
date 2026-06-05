# alerts_viewer.py - لوحة عرض وإدارة التنبيهات

import streamlit as st
import pandas as pd
from datetime import datetime


def show_alerts_panel(t):
    """عرض لوحة التنبيهات المصغرة في لوحة التحكم"""
    
    try:
        from database import db_manager
        
        alerts = db_manager.get_active_alerts(limit=10)
        
        if not alerts:
            return
        
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        warning_alerts = [a for a in alerts if a.get('severity') == 'warning']
        
        if critical_alerts or warning_alerts:
            with st.expander(f"🔔 التنبيهات ({len(alerts)})", expanded=len(critical_alerts) > 0):
                for alert in critical_alerts:
                    st.error(f"""
                    **⚠️ {alert.get('title', 'تنبيه')}**
                    {alert.get('message', '')}
                    """)
                
                for alert in warning_alerts[:5]:
                    st.warning(f"""
                    **{alert.get('title', 'تنبيه')}**
                    {alert.get('message', '')}
                    """)
                
                if st.button("🗑️ حذف جميع التنبيهات", key="clear_alerts_btn"):
                    for alert in alerts:
                        db_manager.dismiss_alert(alert['id'], st.session_state.get('user_name', ''))
                    st.rerun()
                    
    except Exception as e:
        pass


def show_alerts_page(t):
    """صفحة إدارة التنبيهات الكاملة"""
    
    from database import db_manager
    
    st.header(t.get("alerts_title", "🔔 إدارة التنبيهات"))
    
    tab1, tab2 = st.tabs([
        t.get("alerts_tab_active", "🔔 التنبيهات النشطة"),
        t.get("alerts_tab_history", "📜 سجل التنبيهات")
    ])
    
    with tab1:
        alerts = db_manager.get_active_alerts(limit=100)
        
        if not alerts:
            st.success(t.get("alerts_no_active", "✅ لا توجد تنبيهات نشطة"))
            return
        
        for alert in alerts:
            severity_icon = "🔴" if alert.get('severity') == 'critical' else "🟡" if alert.get('severity') == 'warning' else "🔵"
            
            with st.container():
                col1, col2, col3 = st.columns([8, 1, 1])
                with col1:
                    st.markdown(f"""
                    **{severity_icon} {alert.get('title', '')}**
                    {alert.get('message', '')}
                    """)
                    created_at = alert.get('created_at')
                    if created_at:
                        if hasattr(created_at, 'strftime'):
                            st.caption(f"📅 {created_at.strftime('%Y-%m-%d %H:%M')}")
                        else:
                            st.caption(f"📅 {created_at}")
                with col2:
                    if st.button("✓ قرأت", key=f"read_{alert['id']}"):
                        db_manager.mark_alert_read(alert['id'])
                        st.rerun()
                with col3:
                    if st.button("🗑️ حذف", key=f"dismiss_{alert['id']}"):
                        db_manager.dismiss_alert(alert['id'], st.session_state.get('user_name', ''))
                        st.rerun()
                st.divider()
    
    with tab2:
        all_alerts = db_manager.get_all_alerts(include_dismissed=True, limit=200)
        
        if not all_alerts:
            st.info(t.get("alerts_no_history", "📭 لا يوجد سجل للتنبيهات"))
            return
        
        df = pd.DataFrame(all_alerts)
        if not df.empty:
            display_cols = ['id', 'alert_type', 'severity', 'title', 'created_at', 'is_dismissed']
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available_cols], width='stretch')