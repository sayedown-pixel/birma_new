import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from database import db_manager
from utils import send_telegram, get_machine_map, create_machine_file, get_scheduled_tasks, find_image_path
import plotly.graph_objects as go
import plotly.express as px
from helpers import normalize_line_name

def show_maintenance(selected_line, t):
    """Display maintenance page"""
    from helpers import normalize_line_name, send_telegram
    from datetime import datetime
    import streamlit as st
    import pandas as pd
    import os
    
    line_display = normalize_line_name(selected_line)
    st.header(f"{t.get('maint_header', 'Maintenance')} - {line_display}")
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
    
    # ==================== صيانة دورية (Planned maintenance) ====================
    if m_type == t["maint_types"][0]:
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
                (df_maint_today['line'] == selected_line) &
                (df_maint_today['machine'] == machine)
            ]
            
            if not df_maint_today.empty:
                executed_tasks = df_maint_today['task'].tolist()
                tasks = tasks[~tasks['Name'].isin(executed_tasks)]

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
                    placeholder=t.get("enter_technician_name", "Enter technician name"),
                    key="planned_tech_input"
                )
                recs = []
                
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
                                st.image(img_path, width='stretch')
                            done = st.checkbox(t["done"], key=f"planned_done_{i}")
                        
                        if done:
                            recs.append({
                                "type": "planned",
                                "date": datetime.now().date(),
                                "line": selected_line,
                                "machine": machine,
                                "technician": tech,
                                "task": task_name,
                                "issue": "",
                                "start_time": "",
                                "end_time": "",
                                "downtime_minutes": 0,
                                "downtime_category": "",
                                "notes": notes,
                            })
                
                if st.form_submit_button(t["save_btn"], width='stretch'):
                    if not tech or tech.strip() == "":
                        st.error(t.get("maint_enter_tech", "⚠️ Enter technician name first"))
                    elif recs:
                        for rec in recs:
                            try:
                                record_id = db_manager.save_maintenance(rec)
                                #try:
                                #    msg = f"""✅ <b>صيانة دورية منفذة</b>
                                #    ⚙️ الماكينة: {rec['machine']}
                                 #   📏 الخط: {rec['line']}
                                  #  👨‍🔧 الفني: {rec['technician']}
                                   # 📋 المهمة: {rec['task']}
                                    #🆔 رقم السجل: {record_id}"""
                                   # send_telegram(msg)
                                #except:
                                 #   pass
                            except Exception as e:
                                st.error(f"{t.get('maint_save_error', '❌ Failed to save data')}: {e}")
                        st.success(f"✅ {t.get('maint_saved', 'Saved')} {len(recs)} {t.get('task_name', 'tasks')}")
                        st.rerun()
                    else:
                        st.warning(t.get("maint_no_tasks", "No tasks were selected as completed"))
    
    # ==================== صيانة أعطال (Breakdown maintenance) ====================
    else:  # ✅ هذا هو قسم الأعطال
        st.markdown("---")
        st.subheader("🔧 " + t.get("breakdown_report", "Breakdown Report"))
        
        with st.form("breakdown_form"):
            # صف أول: الفني
            col1, col2 = st.columns(2)
            with col1:
                tech = st.text_input(
                    t["tech_label"],
                    placeholder=t.get("enter_technician_name", "Enter technician name"),
                    key="breakdown_tech_input"
                )
            with col2:
                downtime_category = st.selectbox(
                    t.get("maint_breakdown_category", "Stop Type"), 
                    t.get("maint_categories", ["Mechanical", "Electrical", "Operational", "Raw Materials", "Other"]),
                    key="breakdown_category_select"
                )
            
            issue = st.text_area(
                t["issue_label"], 
                height=100, 
                placeholder=t.get("fill_issue", "Issue description"),
                key="breakdown_issue_input"
            )

            # وقت التوقف
            st.markdown("---")
            st.markdown("**⏱️ " + t.get("downtime_period", "Downtime Period") + "**")
            
            col1, col2 = st.columns(2)
            with col1:
                start_time = st.time_input(
                    t["start_t"], 
                    value=datetime.now().time(),
                    key="breakdown_start_time"
                )
                start_date = st.date_input(
                    t.get("maint_breakdown_date_start", "Stop Start Date"), 
                    datetime.now(),
                    key="breakdown_start_date"
                )
            with col2:
                end_time = st.time_input(
                    t["end_t"], 
                    value=datetime.now().time(),
                    key="breakdown_end_time"
                )
                end_date = st.date_input(
                    t.get("maint_repair_date_end", "Repair End Date"), 
                    datetime.now(),
                    key="breakdown_end_date"
                )

            # قطع الغيار والملاحظات
            st.markdown("---")
            spare_parts = st.text_area(
                t.get("maint_spare_parts", "Spare Parts Used"), 
                height=80, 
                placeholder=t.get("maint_spare_parts_help", "Enter names of spare parts used"),
                help=t.get("maint_spare_parts_help", "Enter names of spare parts used in the repair"),
                key="breakdown_spare_parts"
            )
            notes = st.text_area(
                t["note_label"], 
                placeholder=t.get("note_label", "Notes"),
                key="breakdown_notes"
            )

            # زر الحفظ
            submitted = st.form_submit_button(t["save_btn"], width='stretch', type="primary")
            
            if submitted:
                errors = []
                if not tech or tech.strip() == "":
                    errors.append(t.get("fill_technician", "Technician name"))
                if not issue or issue.strip() == "":
                    errors.append(t.get("fill_issue", "Issue description"))
                
                if errors:
                    st.error(t.get("please_enter", "⚠️ Please enter: {fields}").format(fields=", ".join(errors)))
                else:
                    start_datetime = datetime.combine(start_date, start_time)
                    end_datetime = datetime.combine(end_date, end_time)
                    
                    if end_datetime <= start_datetime:
                        st.error(t.get("repair_after_stop", "⚠️ Repair end time must be after stop start time"))
                    else:
                        downtime_minutes = int((end_datetime - start_datetime).total_seconds() / 60)

                        maintenance_data = {
                            "type": "breakdown",
                            "date": datetime.now().date(),
                            "line": selected_line,
                            "machine": machine,
                            "technician": tech,
                            "issue": issue,
                            "task": "",
                            "start_time": start_time.strftime("%H:%M"),
                            "end_time": end_time.strftime("%H:%M"),
                            "downtime_minutes": downtime_minutes,
                            "downtime_category": downtime_category,
                            "spare_parts": spare_parts,
                            "notes": notes,
                        }

                        try:
                            record_id = db_manager.save_maintenance(maintenance_data)
                            st.success(f"✅ {t.get('maint_breakdown_saved', 'Breakdown reported successfully')} (ID: {record_id})")

                            # إرسال إشعار Telegram
                            try:
                                msg = f"""🔧 <b>عطل جديد</b>
⚙️ الماكينة: {machine}
📏 الخط: {selected_line}
👨‍🔧 الفني: {tech}
⏱️ مدة التوقف: {downtime_minutes} دقيقة
📝 الوصف: {issue[:100]}
🆔 رقم البلاغ: {record_id}"""
                                send_telegram(msg)
                            except Exception as tele_e:
                                print(f"Telegram error: {tele_e}")

                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {t.get('maint_save_error', 'Failed to save data')}: {e}")

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
                st.plotly_chart(fig_machine, width='stretch')

                st.dataframe(machine_stats, width='stretch')

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
                st.plotly_chart(fig_category, width='stretch')

                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(category_stats, width='stretch')

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
                st.plotly_chart(fig_trend, width='stretch')

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
                st.dataframe(recent_breakdowns[available_cols], width='stretch')

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