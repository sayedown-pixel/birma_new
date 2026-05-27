import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from database import db_manager
from utils import send_telegram, get_machine_map, create_machine_file, get_scheduled_tasks, find_image_path
import plotly.graph_objects as go
import plotly.express as px

def show_maintenance(selected_line, t):
    """Display maintenance page"""
    st.header(t["maint_header"])
    lang = st.session_state.get("lang", "ar")
    machine_map = get_machine_map(lang)

    # إضافة تبويب للتحليل الذكي
    tab_main, tab_analytics = st.tabs([
        t.get("maint_tab_register", "🔧 Register Maintenance"), 
        t.get("maint_tab_analytics", "📊 Smart Analytics")
    ])

    with tab_main:
        # اختيار نوع الصيانة
        m_type = st.radio(
            t.get("maint_stop_type", "Type"), 
            t["maint_types"], 
            horizontal=True,
            key="maint_type_radio"
        )
    
    # اختيار الماكينة
    machine = st.selectbox(
        t["machine_select"], 
        list(machine_map.keys()),
        key="machine_select_main"
    )
    
    if m_type == t["maint_types"][0]:  # صيانة دورية (Planned maintenance)
        path = machine_map[machine]
        if not os.path.exists(path):
            create_machine_file(path)
        
        try:
            # قراءة ملف الصيانة
            if "Compressor" in path or "AF_Compressor" in path:
                df_tasks = pd.read_excel(path, header=2)
                column_mapping = {
                    'cat': 'Cat', 'no': 'No', 'name': 'Name', 'photo': 'Photo',
                    'tools': 'Tools', 'proc': 'Proc', 'freq': 'Freq',
                    'stat': 'Stat', 'note': 'Note', 'staff': 'Staff'
                }
                for old, new in column_mapping.items():
                    if old in df_tasks.columns:
                        df_tasks = df_tasks.rename(columns={old: new})
                
                required_cols = ['Cat', 'No', 'Name', 'Photo', 'Tools', 'Proc', 'Freq', 'Stat', 'Note', 'Staff']
                for col in required_cols:
                    if col not in df_tasks.columns:
                        df_tasks[col] = ''
                
                df_tasks = df_tasks.dropna(subset=['Name'], how='all')
                df_tasks = df_tasks[df_tasks['Name'].notna()]
                df_tasks = df_tasks.reset_index(drop=True)
            else:
                df_tasks = pd.read_excel(path, skiprows=2)
                df_tasks.columns = ['Cat', 'No', 'Name', 'Photo', 'Tools', 'Proc', 'Freq', 'Stat', 'Note', 'Staff']
        except Exception as e:
            st.error(f"{t.get('maint_file_error', 'Error reading maintenance file')}: {e}")
            df_tasks = pd.DataFrame()
        
        tasks = get_scheduled_tasks(df_tasks)

        # فلترة المهام المنفذة اليوم
        today = datetime.now().date()
        df_maint_today = db_manager.get_all_maintenance()

        if df_maint_today is not None and not df_maint_today.empty:
            df_maint_today['date'] = pd.to_datetime(df_maint_today['date']).dt.date
            df_maint_today = df_maint_today[
                (df_maint_today['date'] == today) & 
                (df_maint_today['type'] == 'planned') &
                (df_maint_today['line'] == selected_line) &  # ✅ فلترة حسب الخط
                (df_maint_today['machine'] == machine)       # ✅ فلترة حسب الماكينة
            ]
            
            if not df_maint_today.empty:
                executed_tasks = df_maint_today['task'].tolist()
                tasks = tasks[~tasks['Name'].isin(executed_tasks)]

# maintenance.py - الجزء المعدل بالكامل لفلترة المهام

        if tasks.empty:
            if datetime.now().strftime('%A') == 'Friday':
                st.warning(t["weekend_msg"])
            else:
                st.success(t.get("maint_all_done", "✅ All scheduled tasks completed for today"))
        else:
            with st.form("planned_maintenance_form"):
                tech = st.text_input(
                    t["tech_label"], 
                    value="", 
                    placeholder=t.get("enter_technician_name", "أدخل اسم الفني"),
                    key="planned_tech_input"
                )
                recs = []
                
                # عرض المهام المتبقية فقط
                for i, row in tasks.iterrows():
                    task_name = row.get('Name', f'Task {i+1}')
                    with st.expander(f"🔧 {task_name} ({row.get('Freq', 'N/A')})"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**🛠️ {t['tools_label']}** {row.get('Tools', 'N/A')}")
                            st.info(f"**📋 {t['proc_label']}**\n{row.get('Proc', 'N/A')}")
                            notes = st.text_input(t["note_label"], key=f"planned_note_{i}")
                        with col2:
                            photo_name = row.get('Photo', '') if pd.notna(row.get('Photo', '')) else ""
                            img_path = find_image_path(photo_name)
                            if img_path:
                                st.image(img_path, use_container_width=True)
                            done = st.checkbox(t["done"], key=f"planned_done_{i}")
                        
                        if done:
                            recs.append({
                                "type": "planned",
                                "date": datetime.now().date(),
                                "line": selected_line,  # ✅ الخط المحدد
                                "machine": machine,      # ✅ الماكينة المحددة
                                "technician": tech,
                                "task": task_name,
                                "issue": "",
                                "start_time": "",
                                "end_time": "",
                                "downtime_minutes": 0,
                                "downtime_category": "",
                                "notes": notes,
                            })
                
                if st.form_submit_button(t["save_btn"], use_container_width=True):
                    if not tech or tech.strip() == "":
                        st.error(t.get("maint_enter_tech", "⚠️ Enter technician name first"))
                    elif recs:
                        for rec in recs:
                            try:
                                record_id = db_manager.save_maintenance(rec)
                                # ✅ تسجيل حدث الصيانة
                                try:
                                    if hasattr(db_manager, 'add_info_log'):
                                        db_manager.add_info_log(
                                            'maintenance',
                                            f"Maintenance completed: {rec['task']} on {rec['machine']} ({rec['line']})",
                                            f"Record ID: {record_id}, Technician: {rec['technician']}"
                                        )
                                except:
                                    pass
                            except Exception as e:
                                st.error(f"{t.get('maint_save_error', '❌ Failed to save data')}: {e}")
                        st.success(f"✅ {t.get('maint_saved', 'Saved')} {len(recs)} {t.get('task_name', 'tasks')}")
                        st.rerun()
                    else:
                        st.warning(t.get("maint_no_tasks", "No tasks were selected as completed"))

    with tab_analytics:
        show_maintenance_analytics(selected_line, t, lang, machine_map)


def show_maintenance_analytics(selected_line, t, lang, machine_map):
    """عرض التحليل الذكي للصيانة"""
    st.subheader(t.get("maint_analytics_title", "📊 Smart Analytics - Faults & Machine Performance"))

    try:
        df_maint = db_manager.get_all_maintenance()

        if df_maint is None or df_maint.empty:
            st.info(t.get("maint_no_data", "📭 No maintenance data for analysis"))
            return

        # فلترة البيانات حسب الخط المحدد
        if "line" in df_maint.columns:
            df_maint = df_maint[df_maint["line"] == selected_line]

        if df_maint.empty:
            st.info(f"{t.get('maint_no_line_data', '📭 No maintenance data for line')}: {selected_line}")
            return

        # عرض ملخص إحصائي
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        total_records = len(df_maint)
        breakdown_records = len(df_maint[df_maint["type"] == "breakdown"]) if "type" in df_maint.columns else 0
        total_downtime = df_maint["downtime_minutes"].sum() if "downtime_minutes" in df_maint.columns else 0

        with col1:
            st.metric(t.get("maint_total_records", "📋 Total Records"), total_records)
        with col2:
            st.metric(t.get("maint_breakdown_count", "⚠️ Breakdowns"), breakdown_records)
        with col3:
            st.metric(t.get("maint_total_downtime_min", "⏱️ Total Downtime (min)"), f"{total_downtime:,.0f}")
        with col4:
            st.metric(t.get("maint_total_downtime_hr", "⏱️ Total Downtime (hrs)"), f"{total_downtime/60:,.1f}")

        st.markdown("---")

        # تحليل الأعطال حسب الماكينة
        if "machine" in df_maint.columns and "downtime_minutes" in df_maint.columns:
            st.subheader(t.get("maint_analysis_by_machine", "🔧 Fault Analysis by Machine"))

            machine_stats = df_maint.groupby("machine").agg({
                "downtime_minutes": "sum",
                "id": "count"
            }).reset_index()
            machine_stats.columns = [t.get("col_machine", "Machine"), t.get("maint_total_downtime_min", "Total Downtime (min)"), t.get("maint_breakdown_count", "Breakdowns")]

            if not machine_stats.empty:
                fig_machine = px.bar(
                    machine_stats,
                    x=t.get("col_machine", "Machine"),
                    y=t.get("maint_total_downtime_min", "Total Downtime (min)"),
                    color=t.get("maint_breakdown_count", "Breakdowns"),
                    title=t.get("maint_analysis_by_machine", "Fault Analysis by Machine"),
                    color_continuous_scale="Reds"
                )
                fig_machine.update_layout(height=400)
                st.plotly_chart(fig_machine, use_container_width=True)

                st.dataframe(machine_stats, use_container_width=True)

        # تحليل الأعطال حسب النوع
        if "downtime_category" in df_maint.columns:
            st.markdown("---")
            st.subheader(t.get("maint_analysis_by_type", "📊 Fault Analysis by Type"))

            category_stats = df_maint[df_maint["downtime_category"].notna()].groupby("downtime_category").agg({
                "downtime_minutes": "sum",
                "id": "count"
            }).reset_index()
            category_stats.columns = [t.get("maint_breakdown_category", "Type"), t.get("maint_total_downtime_min", "Total Downtime (min)"), t.get("records_count", "Count")]

            if not category_stats.empty:
                fig_category = px.pie(
                    category_stats,
                    values=t.get("maint_total_downtime_min", "Total Downtime (min)"),
                    names=t.get("maint_breakdown_category", "Type"),
                    title=t.get("maint_analysis_by_type", "Fault Distribution by Type"),
                    hole=0.4
                )
                fig_category.update_layout(height=400)
                st.plotly_chart(fig_category, use_container_width=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(category_stats, use_container_width=True)

        # تحليل الاتجاه الزمني للأعطال
        if "date" in df_maint.columns:
            st.markdown("---")
            st.subheader(t.get("maint_trend_analysis", "📈 Fault Time Trend"))

            df_maint["date"] = pd.to_datetime(df_maint["date"])
            df_maint["month"] = df_maint["date"].dt.to_period("M")

            monthly_stats = df_maint.groupby("month").agg({
                "downtime_minutes": "sum",
                "id": "count"
            }).reset_index()
            monthly_stats["month"] = monthly_stats["month"].astype(str)
            monthly_stats.columns = [t.get("records_label", "Month"), t.get("maint_total_downtime_min", "Total Downtime (min)"), t.get("maint_breakdown_count", "Breakdowns")]

            if not monthly_stats.empty:
                fig_trend = go.Figure()
                _col_month = monthly_stats.columns[0]
                _col_dt = monthly_stats.columns[1]
                _col_bk = monthly_stats.columns[2]
                fig_trend.add_trace(go.Scatter(
                    x=monthly_stats[_col_month],
                    y=monthly_stats[_col_dt],
                    mode="lines+markers",
                    name=_col_dt,
                    line=dict(color="#ef4444", width=3)
                ))
                fig_trend.add_trace(go.Scatter(
                    x=monthly_stats[_col_month],
                    y=monthly_stats[_col_bk],
                    mode="lines+markers",
                    name=_col_bk,
                    line=dict(color="#f59e0b", width=3),
                    yaxis="y2"
                ))
                fig_trend.update_layout(
                    title=t.get("maint_trend_analysis", "Fault Time Trend"),
                    xaxis_title=_col_month,
                    yaxis_title=_col_dt,
                    yaxis2=dict(
                        title=_col_bk,
                        overlaying="y",
                        side="right"
                    ),
                    height=400,
                    hovermode="x unified"
                )
                st.plotly_chart(fig_trend, use_container_width=True)

        # توصيات الصيانة التنبؤية
        st.markdown("---")
        st.subheader(t.get("maint_predictive_title", "🤖 Predictive Maintenance Recommendations"))

        recommendations = generate_maintenance_recommendations(df_maint, machine_map)

        if recommendations:
            for rec in recommendations:
                if rec["priority"] == "high":
                    st.error(f"🔴 {rec['message']}")
                elif rec["priority"] == "medium":
                    st.warning(f"🟡 {rec['message']}")
                else:
                    st.info(f"🟢 {rec['message']}")
        else:
            st.success(t.get("maint_all_good", "✅ All machines are in good condition"))

        # عرض سجل الأعطال الأخير
        st.markdown("---")
        st.subheader(t.get("maint_recent_breakdowns", "📋 Recent Breakdowns"))

        if "date" in df_maint.columns:
            recent_breakdowns = df_maint[df_maint["type"] == "breakdown"].sort_values("date", ascending=False).head(10)
            if not recent_breakdowns.empty:
                display_cols = ["date", "machine", "issue", "downtime_minutes", "downtime_category", "technician"]
                available_cols = [c for c in display_cols if c in recent_breakdowns.columns]
                st.dataframe(recent_breakdowns[available_cols], use_container_width=True)

    except Exception as e:
        st.error(f"{t.get('maint_analysis_error', '❌ Analysis error')}: {e}")


def generate_maintenance_recommendations(df_maint, machine_map):
    """توليد توصيات الصيانة التنبؤية"""
    recommendations = []

    try:
        if "machine" in df_maint.columns and "downtime_minutes" in df_maint.columns:
            # تحليل كل ماكينة
            for machine in df_maint["machine"].unique():
                machine_data = df_maint[df_maint["machine"] == machine]

                # إجمالي وقت التوقف
                total_downtime = machine_data["downtime_minutes"].sum()

                # عدد الأعطال
                breakdown_count = len(machine_data[machine_data["type"] == "breakdown"])

                # متوسط وقت التوقف
                avg_downtime = machine_data["downtime_minutes"].mean()

                # التوصيات بناءً على البيانات
                if total_downtime > 300:  # أكثر من 5 ساعات
                    lang_ar = st.session_state.get("lang", "ar") == "ar"
                    if lang_ar:
                        msg = f"الماكينة {machine}: إجمالي التوقف {total_downtime:.0f} دقيقة - يوصى بمراجعة شاملة"
                    else:
                        msg = f"Machine {machine}: Total downtime {total_downtime:.0f} min - Comprehensive review recommended"
                    recommendations.append({"priority": "high", "message": msg})

                if breakdown_count >= 3:
                    lang_ar = st.session_state.get("lang", "ar") == "ar"
                    if lang_ar:
                        msg = f"الماكينة {machine}: {breakdown_count} أعطال - يوصى بزيادة تكرار الصيانة الدورية"
                    else:
                        msg = f"Machine {machine}: {breakdown_count} faults - Increase preventive maintenance frequency recommended"
                    recommendations.append({"priority": "medium", "message": msg})

                if avg_downtime > 60:  # متوسط أكثر من ساعة
                    lang_ar = st.session_state.get("lang", "ar") == "ar"
                    if lang_ar:
                        msg = f"الماكينة {machine}: متوسط وقت التوقف {avg_downtime:.0f} دقيقة - يوصى بتحليل أسباب الأعطال"
                    else:
                        msg = f"Machine {machine}: Avg downtime {avg_downtime:.0f} min - Analyze fault causes recommended"
                    recommendations.append({"priority": "medium", "message": msg})

        # تحليل حسب نوع التوقف
        if "downtime_category" in df_maint.columns:
            category_counts = df_maint["downtime_category"].value_counts()
            for category, count in category_counts.items():
                if count >= 3:
                    lang_ar = st.session_state.get("lang", "ar") == "ar"
                    if lang_ar:
                        msg = f"نوع التوقف {category}: {count} مرات - يوصى بالتركيز على هذا النوع من الأعطال"
                    else:
                        msg = f"Stop type {category}: {count} times - Focus on this type of fault recommended"
                    recommendations.append({"priority": "medium", "message": msg})

    except Exception as e:
        pass

    return recommendations