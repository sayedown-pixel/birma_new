# logs_viewer.py - صفحة عرض سجلات النظام

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import db_manager

def show_logs_viewer(t):
    """عرض سجلات النظام"""
    st.header("📋 " + t.get("logs_title", "System Logs"))
    
    # إضافة تبويب للتنظيف
    tab_view, tab_stats, tab_cleanup = st.tabs([
        t.get("logs_tab_view", "📄 View Logs"),
        t.get("logs_tab_stats", "📊 Statistics"),
        t.get("logs_tab_cleanup", "🗑️ Cleanup")
    ])
    
    # ==================== تبويب عرض السجلات ====================
    with tab_view:
        st.markdown(t.get("logs_filter_title", "### Filter Logs"))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            event_types = ["All", "login", "logout", "production", "maintenance", "inventory", "error", "warning"]
            selected_type = st.selectbox(t.get("logs_event_type", "Event Type"), event_types, key="log_type_filter")
        
        with col2:
            event_levels = ["All", "INFO", "WARNING", "ERROR", "CRITICAL"]
            selected_level = st.selectbox(t.get("logs_event_level", "Level"), event_levels, key="log_level_filter")
        
        with col3:
            selected_user = st.text_input(t.get("logs_username", "Username"), placeholder="Filter by username", key="log_user_filter")
        
        with col4:
            days = st.selectbox(t.get("logs_days", "Days"), [7, 14, 30, 60, 90], index=2, key="log_days_filter")
        
        # جلب السجلات
        start_date = datetime.now() - timedelta(days=days)
        
        logs = db_manager.get_logs(
            limit=500,
            event_type=None if selected_type == "All" else selected_type,
            event_level=None if selected_level == "All" else selected_level,
            username=selected_user if selected_user else None,
            start_date=start_date
        )
        
        if logs:
            df = pd.DataFrame(logs)
            
            # تنسيق التاريخ
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # تسمية الأعمدة
            column_labels = {
                'id': t.get("col_id", "ID"),
                'event_type': t.get("logs_event_type", "Type"),
                'event_level': t.get("logs_event_level", "Level"),
                'username': t.get("logs_username", "User"),
                'action': t.get("logs_action", "Action"),
                'details': t.get("logs_details", "Details"),
                'created_at': t.get("col_date", "Date")
            }
            df = df.rename(columns={k: v for k, v in column_labels.items() if k in df.columns})
            
            # عرض الجدول
            st.dataframe(df, use_container_width=True, height=500)
            
            # إحصائيات سريعة
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(t.get("logs_total", "Total"), len(logs))
            with col2:
                errors = len([l for l in logs if l['event_level'] in ['ERROR', 'CRITICAL']])
                st.metric(t.get("logs_errors", "Errors"), errors)
            with col3:
                warnings = len([l for l in logs if l['event_level'] == 'WARNING'])
                st.metric(t.get("logs_warnings", "Warnings"), warnings)
            with col4:
                info = len([l for l in logs if l['event_level'] == 'INFO'])
                st.metric(t.get("logs_info", "Info"), info)
        else:
            st.info(t.get("logs_no_data", "📭 No logs found for the selected criteria"))
    
    # ==================== تبويب الإحصائيات ====================
    with tab_stats:
        st.markdown(t.get("logs_stats_title", "### Logs Statistics"))
        
        # جلب جميع السجلات لآخر 30 يوم
        start_date = datetime.now() - timedelta(days=30)
        logs = db_manager.get_logs(limit=5000, start_date=start_date)
        
        if logs:
            df = pd.DataFrame(logs)
            df['date'] = pd.to_datetime(df['created_at']).dt.date
            
            # إحصائيات حسب النوع
            st.subheader(t.get("logs_stats_by_type", "📊 By Event Type"))
            type_stats = df['event_type'].value_counts().reset_index()
            type_stats.columns = [t.get("logs_event_type", "Type"), t.get("logs_count", "Count")]
            st.dataframe(type_stats, use_container_width=True)
            
            # إحصائيات حسب المستوى
            st.subheader(t.get("logs_stats_by_level", "⚠️ By Event Level"))
            level_stats = df['event_level'].value_counts().reset_index()
            level_stats.columns = [t.get("logs_event_level", "Level"), t.get("logs_count", "Count")]
            st.dataframe(level_stats, use_container_width=True)
            
            # إحصائيات حسب المستخدم
            st.subheader(t.get("logs_stats_by_user", "👤 By User"))
            user_stats = df['username'].value_counts().head(10).reset_index()
            user_stats.columns = [t.get("logs_username", "User"), t.get("logs_count", "Count")]
            st.dataframe(user_stats, use_container_width=True)
            
            # رسم بياني يومي
            st.subheader(t.get("logs_daily_trend", "📈 Daily Trend"))
            daily_counts = df.groupby('date').size().reset_index()
            daily_counts.columns = [t.get("col_date", "Date"), t.get("logs_count", "Count")]
            
            import plotly.express as px
            fig = px.line(daily_counts, x=t.get("col_date", "Date"), y=t.get("logs_count", "Count"),
                          title=t.get("logs_daily_trend", "Daily Log Entries"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(t.get("logs_no_data", "📭 No logs available for statistics"))
    
    # ==================== تبويب التنظيف ====================
    with tab_cleanup:
        st.markdown(t.get("logs_cleanup_title", "### Cleanup Old Logs"))
        st.warning(t.get("logs_cleanup_warning", "⚠️ This will permanently delete old logs. This action cannot be undone."))
        
        col1, col2 = st.columns(2)
        with col1:
            days_to_keep = st.number_input(t.get("logs_keep_days", "Keep logs from last (days)"), 
                                           min_value=7, max_value=365, value=30, step=7)
        with col2:
            # عرض عدد السجلات التي سيتم حذفها
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            old_logs_count = len(db_manager.get_logs(limit=10000, end_date=cutoff_date))
            st.metric(t.get("logs_to_delete", "Logs to delete"), old_logs_count)
        
        if st.button(t.get("logs_cleanup_btn", "🗑️ Delete Old Logs"), type="primary", use_container_width=True):
            if old_logs_count > 0:
                confirm = st.text_input(t.get("logs_confirm", "Type 'DELETE' to confirm"), type="password")
                if confirm == "DELETE":
                    deleted = db_manager.cleanup_old_logs(days_to_keep)
                    st.success(f"✅ {t.get('logs_deleted_success', 'Deleted')} {deleted} {t.get('logs_records', 'records')}")
                    st.rerun()
                else:
                    st.error(t.get("logs_confirm_error", "Please type 'DELETE' to confirm"))
            else:
                st.info(t.get("logs_no_old", "No old logs to delete"))