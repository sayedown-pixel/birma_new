import streamlit as st
import pandas as pd
import os
from datetime import datetime
from database import db_manager
from utils import send_telegram, get_machine_map, create_machine_file, get_scheduled_tasks, find_image_path

def show_maintenance(selected_line, t):
    """Display maintenance page"""
    st.header(t["maint_header"])
    lang = st.session_state.get("lang", "ar")
    machine_map = get_machine_map(lang)
    
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
        
        if tasks.empty:
            if datetime.now().strftime('%A') == 'Friday':
                st.warning(t["weekend_msg"])
            else:
                st.info(f"📋 لا توجد مهام صيانة دورية لليوم")
        else:
            with st.form("planned_maintenance_form"):
                tech = st.text_input(t["tech_label"])
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
                    if recs:
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