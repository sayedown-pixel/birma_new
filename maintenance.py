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
    tab_main, tab_analytics = st.tabs(["🔧 تسجيل الصيانة", "📊 التحليل الذكي"])

    with tab_main:
        # اختيار نوع الصيانة
        m_type = st.radio("Type", t["maint_types"], horizontal=True)
    
    # اختيار الماكينة
    machine = st.selectbox(t["machine_select"], list(machine_map.keys()))
    
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
            st.error(f"خطأ في قراءة ملف الصيانة: {e}")
            df_tasks = pd.DataFrame()
        
        tasks = get_scheduled_tasks(df_tasks)

        # فلترة المهام المنفذة اليوم
        today = datetime.now().date()
        df_maint_today = db_manager.get_all_maintenance()
        if df_maint_today is not None and not df_maint_today.empty:
            df_maint_today['date'] = pd.to_datetime(df_maint_today['date']).dt.date
            df_maint_today = df_maint_today[df_maint_today['date'] == today]
            df_maint_today = df_maint_today[df_maint_today['type'] == 'planned']

            # استبعاد المهام المنفذة اليوم
            if not df_maint_today.empty:
                executed_tasks = df_maint_today['task'].tolist()
                tasks = tasks[~tasks['Name'].isin(executed_tasks)]

        if tasks.empty:
            if datetime.now().strftime('%A') == 'Friday':
                st.warning(t["weekend_msg"])
            else:
                st.success("✅ تم تنفيذ جميع المهام الدورية لهذا اليوم")
        else:
            with st.form("planned_maintenance_form"):
                tech = st.text_input(t["tech_label"], value="", placeholder="اكتب اسم الفني هنا")
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
                                st.image(img_path, use_container_width=True)
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
                
                if st.form_submit_button(t["save_btn"], use_container_width=True):
                    if not tech or tech.strip() == "":
                        st.error("⚠️ اكتب اسم الفني أولاً")
                    elif recs:
                        for rec in recs:
                            try:
                                db_manager.save_maintenance(rec)
                            except Exception as e:
                                st.error(f"خطأ في حفظ البيانات: {e}")
                        st.success(f"✅ تم حفظ {len(recs)} مهمة صيانة")
                        st.rerun()
                    else:
                        st.warning("لم يتم تحديد أي مهام منفذة")
    
    else:  # صيانة عطل (Breakdown maintenance)
        with st.form("breakdown_form"):
            tech = st.text_input(t["tech_label"])
            issue = st.text_area(t["issue_label"], height=100)

            col1, col2 = st.columns(2)
            with col1:
                start_time = st.time_input(t["start_t"])
                start_date = st.date_input("تاريخ بدء التوقف", datetime.now())
            with col2:
                end_time = st.time_input(t["end_t"])
                end_date = st.date_input("تاريخ نهاية الإصلاح", datetime.now())

            downtime_category = st.selectbox("نوع التوقف", ["ميكانيكي", "كهربائي", "تشغيلي", "مواد خام", "أخرى"])
            spare_parts = st.text_area("قطع الغيار المستخدمة", height=80, help="أدخل أسماء قطع الغيار المستخدمة في الإصلاح")
            notes = st.text_area(t["note_label"])

            if st.form_submit_button(t["save_btn"], use_container_width=True):
                # حساب وقت التوقف بالدقائق
                start_datetime = datetime.combine(start_date, start_time)
                end_datetime = datetime.combine(end_date, end_time)
                downtime_minutes = max(0, int((end_datetime - start_datetime).total_seconds() / 60))

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
                    st.success(f"✅ تم تسجيل بلاغ العطل بنجاح (رقم {record_id})")

                    # إرسال إشعار تلجرام
                    try:
                        send_telegram(f"⚠️ عطل في {machine} - {issue[:50]} - وقت التوقف: {downtime_minutes} دقيقة")
                    except:
                        pass

                    st.rerun()
                except Exception as e:
                    st.error(f"❌ فشل حفظ البيانات: {e}")

    with tab_analytics:
        show_maintenance_analytics(selected_line, t, lang, machine_map)


def show_maintenance_analytics(selected_line, t, lang, machine_map):
    """عرض التحليل الذكي للصيانة"""
    st.subheader("📊 التحليل الذكي للأعطال وأداء الماكينات")

    try:
        df_maint = db_manager.get_all_maintenance()

        if df_maint is None or df_maint.empty:
            st.info("📭 لا توجد بيانات صيانة للتحليل")
            return

        # فلترة البيانات حسب الخط المحدد
        if "line" in df_maint.columns:
            df_maint = df_maint[df_maint["line"] == selected_line]

        if df_maint.empty:
            st.info(f"📭 لا توجد بيانات صيانة للخط: {selected_line}")
            return

        # عرض ملخص إحصائي
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        total_records = len(df_maint)
        breakdown_records = len(df_maint[df_maint["type"] == "breakdown"]) if "type" in df_maint.columns else 0
        total_downtime = df_maint["downtime_minutes"].sum() if "downtime_minutes" in df_maint.columns else 0

        with col1:
            st.metric("📋 إجمالي السجلات", total_records)
        with col2:
            st.metric("⚠️ أعطال", breakdown_records)
        with col3:
            st.metric("⏱️ إجمالي التوقف (دقيقة)", f"{total_downtime:,.0f}")
        with col4:
            st.metric("⏱️ إجمالي التوقف (ساعة)", f"{total_downtime/60:,.1f}")

        st.markdown("---")

        # تحليل الأعطال حسب الماكينة
        if "machine" in df_maint.columns and "downtime_minutes" in df_maint.columns:
            st.subheader("🔧 تحليل الأعطال حسب الماكينة")

            machine_stats = df_maint.groupby("machine").agg({
                "downtime_minutes": "sum",
                "id": "count"
            }).reset_index()
            machine_stats.columns = ["الماكينة", "إجمالي التوقف (دقيقة)", "عدد الأعطال"]

            if not machine_stats.empty:
                fig_machine = px.bar(
                    machine_stats,
                    x="الماكينة",
                    y="إجمالي التوقف (دقيقة)",
                    color="عدد الأعطال",
                    title="إجمالي وقت التوقف حسب الماكينة",
                    color_continuous_scale="Reds"
                )
                fig_machine.update_layout(height=400)
                st.plotly_chart(fig_machine, use_container_width=True)

                st.dataframe(machine_stats, use_container_width=True)

        # تحليل الأعطال حسب النوع
        if "downtime_category" in df_maint.columns:
            st.markdown("---")
            st.subheader("📊 تحليل الأعطال حسب النوع")

            category_stats = df_maint[df_maint["downtime_category"].notna()].groupby("downtime_category").agg({
                "downtime_minutes": "sum",
                "id": "count"
            }).reset_index()
            category_stats.columns = ["نوع التوقف", "إجمالي التوقف (دقيقة)", "عدد المرات"]

            if not category_stats.empty:
                fig_category = px.pie(
                    category_stats,
                    values="إجمالي التوقف (دقيقة)",
                    names="نوع التوقف",
                    title="توزيع الأعطال حسب النوع",
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
            st.subheader("📈 الاتجاه الزمني للأعطال")

            df_maint["date"] = pd.to_datetime(df_maint["date"])
            df_maint["month"] = df_maint["date"].dt.to_period("M")

            monthly_stats = df_maint.groupby("month").agg({
                "downtime_minutes": "sum",
                "id": "count"
            }).reset_index()
            monthly_stats["month"] = monthly_stats["month"].astype(str)
            monthly_stats.columns = ["الشهر", "إجمالي التوقف (دقيقة)", "عدد الأعطال"]

            if not monthly_stats.empty:
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=monthly_stats["الشهر"],
                    y=monthly_stats["إجمالي التوقف (دقيقة)"],
                    mode="lines+markers",
                    name="إجمالي التوقف",
                    line=dict(color="#ef4444", width=3)
                ))
                fig_trend.add_trace(go.Scatter(
                    x=monthly_stats["الشهر"],
                    y=monthly_stats["عدد الأعطال"],
                    mode="lines+markers",
                    name="عدد الأعطال",
                    line=dict(color="#f59e0b", width=3),
                    yaxis="y2"
                ))
                fig_trend.update_layout(
                    title="الاتجاه الزمني للأعطال",
                    xaxis_title="الشهر",
                    yaxis_title="إجمالي التوقف (دقيقة)",
                    yaxis2=dict(
                        title="عدد الأعطال",
                        overlaying="y",
                        side="right"
                    ),
                    height=400,
                    hovermode="x unified"
                )
                st.plotly_chart(fig_trend, use_container_width=True)

        # توصيات الصيانة التنبؤية
        st.markdown("---")
        st.subheader("🤖 توصيات الصيانة التنبؤية")

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
            st.success("✅ جميع الماكينات في حالة جيدة")

        # عرض سجل الأعطال الأخير
        st.markdown("---")
        st.subheader("📋 آخر الأعطال المسجلة")

        if "date" in df_maint.columns:
            recent_breakdowns = df_maint[df_maint["type"] == "breakdown"].sort_values("date", ascending=False).head(10)
            if not recent_breakdowns.empty:
                display_cols = ["date", "machine", "issue", "downtime_minutes", "downtime_category", "technician"]
                available_cols = [c for c in display_cols if c in recent_breakdowns.columns]
                st.dataframe(recent_breakdowns[available_cols], use_container_width=True)

    except Exception as e:
        st.error(f"❌ خطأ في التحليل: {e}")


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
                    recommendations.append({
                        "priority": "high",
                        "message": f"الماكينة {machine}: إجمالي التوقف {total_downtime:.0f} دقيقة - يوصى بمراجعة شاملة"
                    })

                if breakdown_count >= 3:
                    recommendations.append({
                        "priority": "medium",
                        "message": f"الماكينة {machine}: {breakdown_count} أعطال - يوصى بزيادة تكرار الصيانة الدورية"
                    })

                if avg_downtime > 60:  # متوسط أكثر من ساعة
                    recommendations.append({
                        "priority": "medium",
                        "message": f"الماكينة {machine}: متوسط وقت التوقف {avg_downtime:.0f} دقيقة - يوصى بتحليل أسباب الأعطال"
                    })

        # تحليل حسب نوع التوقف
        if "downtime_category" in df_maint.columns:
            category_counts = df_maint["downtime_category"].value_counts()
            for category, count in category_counts.items():
                if count >= 3:
                    recommendations.append({
                        "priority": "medium",
                        "message": f"نوع التوقف {category}: {count} مرات - يوصى بالتركيز على هذا النوع من الأعطال"
                    })

    except Exception as e:
        pass

    return recommendations