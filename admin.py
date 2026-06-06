# admin.py - نسخة نظيفة بدون clean_line_name

import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, timedelta
from database import load_all_production
from utils import USERS, delete_production_record
import plotly.graph_objects as go
import plotly.express as px
from report_generator import generate_production_report_pdf, generate_maintenance_report_pdf
from email_sender import send_weekly_report_email
from database import db_manager
from backup_manager import show_backup_management, run_auto_backup



def show_users(t):
    """Display users management page"""
    st.header(t["users_title"])
    users_df = pd.DataFrame([{"Username": k, "Name": v["name"], "Role": v["role"]} for k, v in USERS.items()])
    st.dataframe(users_df, width='stretch')


def _show_reporting_tab(t):
    """عرض واجهة التقارير المتقدمة"""
    from datetime import datetime, timedelta
    from report_generator import generate_production_report_pdf, generate_maintenance_report_pdf
    
    st.subheader(t.get("admin_reports_title", "📊 Advanced Reports"))
    
    # الحصول على اللغة الحالية
    lang = st.session_state.get('lang', 'ar')
    
    # تبويبات للتقارير المختلفة
    report_tab1, report_tab2, report_tab3 = st.tabs([
        t.get("admin_tab_pdf", "📄 PDF Reports"), 
        t.get("admin_tab_email", "✉️ Send Weekly Report"), 
        t.get("admin_tab_compare", "📈 Line Comparison")
    ])
    
    # ==================== تبويب PDF ====================
    with report_tab1:
        st.markdown(t.get("admin_pdf_title", "### Generate Instant PDF Report"))
        col1, col2 = st.columns(2)
        with col1:
            report_type = st.selectbox(
                t.get("admin_report_type", "Report Type"), 
                t.get("admin_report_types", ["Production", "Maintenance"]), 
                key="report_type_pdf_main"
            )
            start_date = st.date_input(
                t.get("admin_start_date", "Start Date"), 
                datetime.now() - timedelta(days=30),
                key="pdf_start_date_main"
            )
        with col2:
            end_date = st.date_input(
                t.get("admin_end_date", "End Date"), 
                datetime.now(),
                key="pdf_end_date_main"
            )
            _is_prod = report_type == t.get("admin_report_types", ["Production", "Maintenance"])[0]
            line_filter = None
            if _is_prod:
                line_filter = st.selectbox(
                    t.get("admin_line_filter", "Production Line"), 
                    [t.get("admin_all_lines", "All"), "Line 1", "Line 2"],
                    key="line_filter_pdf_main"
                )
        
        if st.button(t.get("admin_create_report", "📑 Generate & Download Report"), key="btn_gen_pdf_main", width='stretch'):
            with st.spinner(t.get("admin_creating", "Generating report...")):
                pdf_path = None
                if _is_prod:
                    line_param = None if line_filter == t.get("admin_all_lines", "All") else line_filter
                    pdf_path = generate_production_report_pdf(start_date, end_date, line_param)
                else:
                    pdf_path = generate_maintenance_report_pdf(start_date, end_date)
                
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label=t.get("admin_download_pdf", "📥 Download Report (PDF)"),
                            data=f,
                            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            width='stretch',
                            key="download_pdf_btn_main"
                        )
                else:
                    st.error(t.get("admin_no_data_report", "❌ No data available for the selected period"))
    
    with report_tab2:
        st.markdown(t.get("admin_email_title", "### Send Automatic Weekly Report"))
        st.info("📧 " + t.get("admin_email_info", "Report will be sent to the specified email immediately"))
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            # ✅ استخدام الترجمة
            send_btn_text = t.get("send_to_all_recipients", "📧 Send report to all recipients (immediate)")
            if st.button(send_btn_text, key="send_to_all", width='stretch'):
                with st.spinner(t.get("sending_report", "Sending reports to all recipients...")):
                    from email_sender import send_weekly_auto_reports
                    send_weekly_auto_reports()
                    st.success(t.get("reports_sent_success", "✅ Reports sent to all recipients"))
        with col_btn2:
            # ✅ استخدام الترجمة
            auto_send_text = t.get("auto_send_schedule", "📅 **Auto send:** Every Monday at 8:00 AM")
            st.info(auto_send_text)
        
        # ✅ نموذج الإرسال لبريد واحد
        with st.form(key="email_report_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                recipient = st.text_input(
                    t.get("admin_recipient", "Recipient Email"), 
                    placeholder="manager@company.com",
                    key="email_recipient_field"
                )
                report_type_email = st.selectbox(
                    t.get("admin_schedule_type", "Report Type"), 
                    t.get("admin_schedule_types", ["Production Report", "Maintenance Report"]),
                    key="report_type_email_select"
                )
            
            with col2:
                line_for_email = st.selectbox(
                    t.get("admin_line_for_email", "Production Line (for report only)"), 
                    [t.get("admin_all_lines", "All"), "Line 1", "Line 2"],
                    key="line_for_email_select"
                )
                st.write("**Report Period:** Last 7 days")
                st.caption(f"From {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
            
            submitted = st.form_submit_button(
                t.get("admin_send_now", "✉️ Send Report Now"), 
                width='stretch',
                type="primary"
            )
            
            if submitted:
                if not recipient:
                    st.error(t.get("admin_email_required", "⚠️ Please enter recipient email"))
                else:
                    with st.spinner(t.get("admin_creating", "Generating report and sending email...")):
                        end = datetime.now()
                        start = end - timedelta(days=7)
                        line_param = None if line_for_email == t.get("admin_all_lines", "All") else line_for_email
                        
                        success, msg = send_weekly_report_email(recipient, start, end, line_param)
                        
                        if success:
                            st.success(f"✅ {msg}")
                            st.balloons()
                        else:
                            st.error(f"❌ {msg}")
    
    # ==================== تبويب مقارنة الخطوط ====================
    with report_tab3:
        st.markdown(t.get("admin_compare_title", "### Compare Production Lines Performance"))
        
        compare_days = st.selectbox(
            t.get("admin_period", "Period"), 
            [7, 14, 30, 60], 
            index=2, 
            key="compare_days_select"
        )
        
        if st.button(t.get("admin_show_comparison", "📊 Show Comparison"), key="btn_compare_main", width='stretch'):
            with st.spinner(t.get("admin_loading", "Loading data...")):
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=compare_days)
                    df = db_manager.get_all_production(start_date=start_date)
                    
                    if df.empty:
                        st.warning(t.get("admin_no_compare_data", "⚠️ No production data for comparison"))
                    else:
                        df['date'] = pd.to_datetime(df['date']).dt.date
                        df_grouped = df.groupby(['date', 'line']).agg({
                            'oee': 'mean',
                            'efficiency': 'mean',
                            'output_units': 'sum'
                        }).reset_index()
                        
                        fig_oee = px.line(
                            df_grouped, x='date', y='oee', color='line',
                            title=t.get("admin_oee_compare_chart", "📊 OEE Comparison (Last {days} Days)").format(days=compare_days),
                            markers=True
                        )
                        fig_oee.update_layout(height=400)
                        st.plotly_chart(fig_oee, width='stretch')
                        
                        fig_eff = px.line(
                            df_grouped, x='date', y='efficiency', color='line',
                            title=t.get("admin_eff_compare_chart", "⚡ Efficiency Comparison (Last {days} Days)").format(days=compare_days),
                            markers=True
                        )
                        fig_eff.update_layout(height=400)
                        st.plotly_chart(fig_eff, width='stretch')
                        
                        fig_prod = px.bar(
                            df_grouped, x='date', y='output_units', color='line',
                            title=t.get("admin_prod_compare_chart", "🏭 Daily Production Comparison (Last {days} Days)").format(days=compare_days),
                            barmode='group'
                        )
                        fig_prod.update_layout(height=400)
                        st.plotly_chart(fig_prod, width='stretch')
                        
                        st.subheader(t.get("admin_performance_summary", "📋 Performance Summary"))
                        summary = df.groupby('line').agg({
                            'oee': 'mean',
                            'efficiency': 'mean',
                            'output_units': 'sum',
                            'downtime_minutes': 'sum'
                        }).round(1)
                        summary.columns = [t.get("admin_summary_oee", "Avg OEE %"), t.get("admin_summary_efficiency", "Avg Efficiency %"), t.get("admin_summary_production", "Total Production"), t.get("admin_summary_downtime", "Total Downtime (min)")]
                        st.dataframe(summary, width='stretch')
                        
                except Exception as e:
                    st.error(f"{t.get('admin_error_occurred', '❌ Error')}: {e}")


def show_settings(t):
    st.header(t["settings_title"])

    tab_general, tab_security, tab_password, tab_reports = st.tabs([
        t.get("admin_tab_general", "⚙️ General"), 
        t.get("admin_tab_security", "🔒 Security"), 
        t.get("admin_tab_password", "🔑 Change Password"), 
        t.get("admin_tab_reports", "📊 Reports")
    ])

    with tab_general:
        col1, col2 = st.columns(2)
        with col1:
            if st.button(t["backup_data"], width='stretch'):
                if os.path.exists("smart_factory.db"):
                    shutil.copy("smart_factory.db", f"backup_sfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                    st.success(t.get("admin_backup_success", "✅ Backup created successfully"))
                elif os.path.exists("birma_data.db"):
                    shutil.copy("birma_data.db", f"backup_birma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                    st.success(t.get("admin_backup_success", "✅ Backup created successfully"))
        with col2:
            if st.button(t["clear_cache"], width='stretch'):
                st.cache_data.clear()
                st.success(t.get("admin_cache_cleared", "✅ Cache cleared successfully"))
            st.markdown("---")
        st.subheader(t.get("backup_advanced_title", "💾 Advanced Backup & Restore"))
        show_backup_management(t)        

    with tab_security:
        st.subheader(t.get("admin_security_title", "🔒 Security Settings"))
        st.info(t.get("admin_security_info", "⏰ **Auto Logout:** After **30 minutes** of inactivity\n\n🔒 **Account Lock:** After **5 failed attempts** for **30 minutes**\n\n📧 **Login:** By email or username"))

        st.markdown("---")
        st.subheader(t.get("admin_unlock_account", "🔓 Unlock Account"))
        users = db_manager.get_all_users()
        locked = [u for u in users if (u.get('failed_attempts') or 0) >= 5]
        if locked:
            for u in locked:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.warning(f"🔒 {u['username']} — {u['name']} ({u.get('failed_attempts',0)} {t.get('admin_failed_attempts', 'failed attempts')})")
                with col2:
                    if st.button(t.get("admin_unlock_btn", "Unlock"), key=f"unlock_{u['id']}"):
                        db_manager.unlock_user(u['id'])
                        st.success(f"{t.get('admin_unlocked', '✅ Account unlocked')} {u['username']}")
                        st.rerun()
        else:
            st.success(t.get("admin_no_locked", "✅ No locked accounts currently"))

    with tab_password:
        st.subheader(t.get("admin_change_password_title", "🔑 Change Password"))
        from auth import change_password
        
        username = st.session_state.get('username', '')
        if not username:
            username = st.session_state.get('user_name', '')
        
        with st.form("change_pw_form"):
            old_pw = st.text_input(t.get("admin_old_password", "Current Password"), type="password")
            new_pw = st.text_input(t.get("admin_new_password", "New Password"), type="password")
            conf_pw = st.text_input(t.get("admin_confirm_password", "Confirm New Password"), type="password")

            if st.form_submit_button(t.get("admin_change_pw_btn", "Change Password"), width='stretch'):
                if not all([old_pw, new_pw, conf_pw]):
                    st.error(t.get("admin_fill_all", "⚠️ Please fill all fields"))
                elif new_pw != conf_pw:
                    st.error(t.get("admin_passwords_mismatch", "⚠️ Passwords do not match"))
                elif len(new_pw) < 4:
                    st.error(t.get("admin_password_too_short", "⚠️ Password must be at least 4 characters"))
                elif change_password(username, old_pw, new_pw):
                    st.success(t.get("admin_password_changed", "✅ Password changed successfully"))
                    st.session_state.must_change_password = False
                    st.balloons()
                else:
                    st.error(t.get("admin_wrong_password", "❌ Current password is incorrect"))
    
    with tab_reports:
        _show_reporting_tab(t)


def show_delete_records(df_raw, df_fg, t):
    """Display delete records section in sidebar"""
    st.sidebar.divider()
    with st.sidebar.expander("🔒 " + t["admin_title"]):
        pw = st.text_input(t["password"], type="password", key="del_pw")
        if pw in ["admin123", "100"]:
            df_prod = load_all_production()
            if not df_prod.empty:
                if 'id' not in df_prod.columns:
                    st.error(t.get("admin_id_not_found", "⚠️ ID column not found in database"))
                else:
                    df_display = df_prod.copy()
                    df_display['desc'] = df_display.apply(
                        lambda row: f"📦 ID:{row['id']} | {row['date']} | {row['product']} | {row['output_units']} {t['quantity']}", 
                        axis=1
                    )
                    
                    selected_desc = st.selectbox(t.get("admin_select_record", "Select record to delete"), options=df_display['desc'].tolist())
                    selected_id = int(selected_desc.split('|')[0].replace('📦 ID:', '').strip())
                    
                    if st.button("🗑️ " + t["delete_btn"], width='stretch'):
                        ok, msg = delete_production_record(selected_id, df_raw, df_fg)
                        if ok:
                            st.success(f"✅ {msg}")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info(t.get("admin_no_records", "No records to delete"))