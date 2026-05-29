# backup_manager.py
import os
import shutil
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import json
import tempfile
from database import db_manager

# ============================================================================
# Configuration
# ============================================================================

BACKUP_DIR = "backups"
AUTO_BACKUP_DIR = os.path.join(BACKUP_DIR, "auto")
MANUAL_BACKUP_DIR = os.path.join(BACKUP_DIR, "manual")
EXPORT_DIR = os.path.join(BACKUP_DIR, "exports")

# إنشاء المجلدات إذا لم تكن موجودة
for dir_path in [BACKUP_DIR, AUTO_BACKUP_DIR, MANUAL_BACKUP_DIR, EXPORT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ============================================================================
# Auto Backup Functions
# ============================================================================

def should_create_backup():
    """التحقق مما إذا كان يجب إنشاء نسخة احتياطية اليوم"""
    backup_log_file = os.path.join(AUTO_BACKUP_DIR, "backup_log.json")
    
    if not os.path.exists(backup_log_file):
        return True
    
    try:
        with open(backup_log_file, 'r') as f:
            log = json.load(f)
            last_backup = datetime.fromisoformat(log.get('last_backup', '2000-01-01'))
            return datetime.now().date() > last_backup.date()
    except:
        return True

def update_backup_log():
    """تحديث سجل النسخ الاحتياطي"""
    backup_log_file = os.path.join(AUTO_BACKUP_DIR, "backup_log.json")
    with open(backup_log_file, 'w') as f:
        json.dump({'last_backup': datetime.now().isoformat()}, f)

def export_table_to_csv(table_name, data):
    """تصدير جدول إلى CSV"""
    if data is None or data.empty:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{table_name}_{timestamp}.csv"
    filepath = os.path.join(AUTO_BACKUP_DIR, filename)
    data.to_csv(filepath, index=False, encoding='utf-8-sig')
    return filepath

def create_database_backup():
    """إنشاء نسخة احتياطية كاملة لقاعدة البيانات"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_info = {
            'timestamp': timestamp,
            'date': datetime.now().isoformat(),
            'tables': {}
        }
        
        # تصدير جميع الجداول
        tables = {
            'production': db_manager.get_all_production(),
            'maintenance': db_manager.get_all_maintenance(),
            'delivery': db_manager.get_all_delivery(),
            'raw_receipts': db_manager.get_all_raw_receipts(),
        }
        
        for table_name, data in tables.items():
            filepath = export_table_to_csv(table_name, data)
            if filepath:
                backup_info['tables'][table_name] = filepath
        
        # حفظ معلومات النسخة الاحتياطية
        info_file = os.path.join(AUTO_BACKUP_DIR, f"backup_{timestamp}.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        # نسخ ملف قاعدة البيانات إذا كان SQLite
        if db_manager.is_using_sqlite():
            db_file = "birma_data.db"
            if os.path.exists(db_file):
                backup_db_file = os.path.join(AUTO_BACKUP_DIR, f"database_{timestamp}.db")
                shutil.copy(db_file, backup_db_file)
                backup_info['database_file'] = backup_db_file
        
        update_backup_log()
        return True, f"✅ تم إنشاء النسخة الاحتياطية {timestamp}"
        
    except Exception as e:
        return False, f"❌ فشل إنشاء النسخة الاحتياطية: {str(e)}"

def run_auto_backup():
    """تشغيل النسخ الاحتياطي التلقائي"""
    if should_create_backup():
        return create_database_backup()
    return True, "✅ لا حاجة لنسخة احتياطية جديدة (تم اليوم)"

# ============================================================================
# Restore Functions
# ============================================================================

def get_available_backups():
    """الحصول على قائمة النسخ الاحتياطية المتاحة"""
    backups = []
    
    # البحث في المجلد التلقائي
    for file in os.listdir(AUTO_BACKUP_DIR):
        if file.startswith("backup_") and file.endswith(".json"):
            filepath = os.path.join(AUTO_BACKUP_DIR, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    backups.append({
                        'type': 'auto',
                        'timestamp': info.get('timestamp', file.replace('backup_', '').replace('.json', '')),
                        'date': info.get('date', ''),
                        'filepath': filepath,
                        'info': info
                    })
            except:
                pass
    
    # البحث في المجلد اليدوي
    for file in os.listdir(MANUAL_BACKUP_DIR):
        if file.startswith("manual_backup_") and file.endswith(".json"):
            filepath = os.path.join(MANUAL_BACKUP_DIR, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    backups.append({
                        'type': 'manual',
                        'timestamp': info.get('timestamp', file.replace('manual_backup_', '').replace('.json', '')),
                        'date': info.get('date', ''),
                        'filepath': filepath,
                        'info': info,
                        'description': info.get('description', '')
                    })
            except:
                pass
    
    # ترتيب حسب التاريخ (الأحدث أولاً)
    backups.sort(key=lambda x: x['date'], reverse=True)
    return backups

def restore_from_backup(backup_info):
    """استعادة البيانات من نسخة احتياطية"""
    try:
        restored_tables = []
        
        for table_name, filepath in backup_info['info']['tables'].items():
            if os.path.exists(filepath):
                df = pd.read_csv(filepath, encoding='utf-8-sig')
                
                # استعادة البيانات حسب نوع الجدول
                if table_name == 'production':
                    for _, row in df.iterrows():
                        db_manager.save_production(row.to_dict())
                elif table_name == 'maintenance':
                    for _, row in df.iterrows():
                        db_manager.save_maintenance(row.to_dict())
                elif table_name == 'delivery':
                    for _, row in df.iterrows():
                        db_manager.save_delivery(row.to_dict())
                elif table_name == 'raw_receipts':
                    for _, row in df.iterrows():
                        db_manager.save_raw_receipt(row.to_dict())
                
                restored_tables.append(table_name)
        
        return True, f"✅ تم استعادة {len(restored_tables)} جدول: {', '.join(restored_tables)}"
        
    except Exception as e:
        return False, f"❌ فشل الاستعادة: {str(e)}"

def create_manual_backup(description=""):
    """إنشاء نسخة احتياطية يدوية"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_info = {
            'timestamp': timestamp,
            'date': datetime.now().isoformat(),
            'description': description,
            'type': 'manual',
            'tables': {}
        }
        
        # تصدير جميع الجداول
        tables = {
            'production': db_manager.get_all_production(),
            'maintenance': db_manager.get_all_maintenance(),
            'delivery': db_manager.get_all_delivery(),
            'raw_receipts': db_manager.get_all_raw_receipts(),
        }
        
        for table_name, data in tables.items():
            if data is not None and not data.empty:
                export_file = os.path.join(MANUAL_BACKUP_DIR, f"{table_name}_{timestamp}.csv")
                data.to_csv(export_file, index=False, encoding='utf-8-sig')
                backup_info['tables'][table_name] = export_file
        
        # حفظ معلومات النسخة الاحتياطية
        info_file = os.path.join(MANUAL_BACKUP_DIR, f"manual_backup_{timestamp}.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        return True, f"✅ تم إنشاء النسخة الاحتياطية اليدوية {timestamp}"
        
    except Exception as e:
        return False, f"❌ فشل إنشاء النسخة الاحتياطية: {str(e)}"

# ============================================================================
# Export Functions
# ============================================================================

def export_all_data_to_excel():
    """تصدير جميع البيانات إلى ملف Excel واحد"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(EXPORT_DIR, f"full_export_{timestamp}.xlsx")
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # تصدير كل جدول في ورقة منفصلة
            tables = {
                'Production': db_manager.get_all_production(),
                'Maintenance': db_manager.get_all_maintenance(),
                'Delivery': db_manager.get_all_delivery(),
                'Raw_Receipts': db_manager.get_all_raw_receipts(),
            }
            
            for sheet_name, data in tables.items():
                if data is not None and not data.empty:
                    data.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
        
        return filepath
        
    except Exception as e:
        return None

def export_to_pdf_report(start_date, end_date, report_type="production"):
    """تصدير تقرير PDF"""
    try:
        from report_generator import generate_production_report_pdf, generate_maintenance_report_pdf
        
        if report_type == "production":
            pdf_path = generate_production_report_pdf(start_date, end_date)
        else:
            pdf_path = generate_maintenance_report_pdf(start_date, end_date)
        
        if pdf_path:
            # نسخ الملف إلى مجلد التصدير
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(EXPORT_DIR, f"report_{report_type}_{timestamp}.pdf")
            shutil.copy(pdf_path, export_path)
            return export_path
        
        return None
        
    except Exception as e:
        print(f"PDF export error: {e}")
        return None

# ============================================================================
# Backup UI Components
# ============================================================================

def show_backup_management(t):
    """عرض واجهة إدارة النسخ الاحتياطي"""
    st.subheader(t.get("backup_management_title", "💾 Backup & Restore Management"))
    
    tab_backup, tab_restore, tab_export = st.tabs([
        t.get("backup_tab_create", "📤 Create Backup"),
        t.get("backup_tab_restore", "🔄 Restore Backup"),
        t.get("backup_tab_export", "📥 Export Data")
    ])
    
    # ==================== تبويب إنشاء نسخة احتياطية ====================
    with tab_backup:
        st.markdown(t.get("backup_create_info", "### Create New Backup"))
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(t.get("backup_auto_btn", "🤖 Run Auto Backup"), width='stretch'):
                with st.spinner(t.get("backup_creating", "Creating backup...")):
                    success, msg = run_auto_backup()
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        
        with col2:
            description = st.text_input(t.get("backup_description", "Description (optional)"), placeholder="e.g., Before major changes")
            if st.button(t.get("backup_manual_btn", "📀 Create Manual Backup"), width='stretch'):
                with st.spinner(t.get("backup_creating", "Creating backup...")):
                    success, msg = create_manual_backup(description)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        
        # عرض النسخ الاحتياطية الأخيرة
        st.markdown("---")
        st.markdown(t.get("backup_recent_title", "### Recent Backups"))
        backups = get_available_backups()
        if backups:
            backup_df = pd.DataFrame([{
                t.get("backup_col_type", "Type"): b['type'],
                t.get("backup_col_timestamp", "Timestamp"): b['timestamp'],
                t.get("backup_col_description", "Description"): b.get('description', ''),
                t.get("backup_col_tables", "Tables"): ', '.join(b['info'].get('tables', {}).keys())
            } for b in backups[:10]])
            st.dataframe(backup_df, width='stretch', hide_index=True)
        else:
            st.info(t.get("backup_no_backups", "📭 No backups found"))
    
    # ==================== تبويب استعادة نسخة ====================
    with tab_restore:
        st.markdown(t.get("backup_restore_info", "### Restore from Backup"))
        st.warning(t.get("backup_restore_warning", "⚠️ Restoring will overwrite current data! Make sure you have a recent backup first."))
        
        backups = get_available_backups()
        if backups:
            backup_options = []
            for b in backups:
                label = f"{b['type'].upper()} - {b['timestamp']}"
                if b.get('description'):
                    label += f" ({b['description']})"
                backup_options.append(label)
            
            selected_backup = st.selectbox(
                t.get("backup_select", "Select backup to restore"),
                backup_options
            )
            
            selected_idx = backup_options.index(selected_backup)
            selected = backups[selected_idx]
            
            # عرض تفاصيل النسخة
            with st.expander(t.get("backup_details", "📋 Backup Details")):
                st.json(selected['info'])
            
            col1, col2 = st.columns([1, 3])
            with col1:
                confirm = st.text_input(t.get("backup_confirm_text", "Type 'RESTORE' to confirm"), type="password")
            
            with col2:
                if confirm == "RESTORE":
                    if st.button(t.get("backup_restore_btn", "🔄 Restore Now"), type="primary", width='stretch'):
                        with st.spinner(t.get("backup_restoring", "Restoring data...")):
                            success, msg = restore_from_backup(selected)
                            if success:
                                st.success(msg)
                                st.cache_data.clear()
                                st.info(t.get("backup_refresh_needed", "🔄 Please refresh the page to see restored data"))
                            else:
                                st.error(msg)
                else:
                    st.caption(t.get("backup_restore_hint", "Enter 'RESTORE' (all caps) to enable restore button"))
        else:
            st.info(t.get("backup_no_backups_restore", "📭 No backups available for restore"))
    
    # ==================== تبويب تصدير البيانات ====================
    with tab_export:
        st.markdown(t.get("backup_export_info", "### Export Data"))
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Excel Export")
            if st.button(t.get("backup_export_excel_btn", "📑 Export All to Excel"), width='stretch'):
                with st.spinner(t.get("backup_exporting", "Exporting data...")):
                    filepath = export_all_data_to_excel()
                    if filepath:
                        with open(filepath, 'rb') as f:
                            st.download_button(
                                label=t.get("backup_download_excel", "📥 Download Excel File"),
                                data=f,
                                file_name=os.path.basename(filepath),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                width='stretch'
                            )
                    else:
                        st.error(t.get("backup_export_failed", "❌ Failed to export data"))
        
        with col2:
            st.markdown("#### 📄 PDF Report")
            export_start = st.date_input(t.get("backup_export_start", "Start Date"), datetime.now() - timedelta(days=30))
            export_end = st.date_input(t.get("backup_export_end", "End Date"), datetime.now())
            export_type = st.selectbox(t.get("backup_export_type", "Report Type"), ["Production", "Maintenance"])
            
            if st.button(t.get("backup_export_pdf_btn", "📄 Generate PDF Report"), width='stretch'):
                with st.spinner(t.get("backup_creating", "Generating PDF...")):
                    report_type = "production" if export_type == "Production" else "maintenance"
                    filepath = export_to_pdf_report(export_start, export_end, report_type)
                    if filepath:
                        with open(filepath, 'rb') as f:
                            st.download_button(
                                label=t.get("backup_download_pdf", "📥 Download PDF Report"),
                                data=f,
                                file_name=os.path.basename(filepath),
                                mime="application/pdf",
                                width='stretch'
                            )
                    else:
                        st.error(t.get("backup_export_failed", "❌ Failed to generate PDF"))
        
        # عرض ملفات التصدير السابقة
        st.markdown("---")
        st.markdown(t.get("backup_export_history", "### Recent Exports"))
        
        export_files = []
        for file in os.listdir(EXPORT_DIR):
            filepath = os.path.join(EXPORT_DIR, file)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                export_files.append({
                    'file': file,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })
        
        if export_files:
            export_files.sort(key=lambda x: x['modified'], reverse=True)
            for f in export_files[:5]:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.caption(f"📄 {f['file']}")
                with col2:
                    st.caption(f"{f['size']/1024:.1f} KB")
                with col3:
                    filepath = os.path.join(EXPORT_DIR, f['file'])
                    with open(filepath, 'rb') as fp:
                        st.download_button("📥", data=fp, file_name=f['file'], key=f"export_{f['file']}")
        else:
            st.caption(t.get("backup_no_exports", "No export files found"))