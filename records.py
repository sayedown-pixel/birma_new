# records.py - نسخة كاملة مع فلاتر متقدمة

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import db_manager, delete_maintenance_record, delete_delivery_record, delete_raw_receipt_record
from utils import get_production_record_labels, delete_production_record
from helpers import normalize_line_name
def show_records(t, lang, df_raw=None, df_fg=None):
    """Display records page with tabs for different record types"""
    st.header(t["records"])

    tab1, tab2, tab3, tab4 = st.tabs([
        t["history_p"],
        t["history_m"],
        t["history_delivery"],
        t.get("records_raw_purchases", "📦 Raw Material Purchases"),
    ])

    with tab1:
        show_production_records(t, df_raw, df_fg)
    
    with tab2:
        show_maintenance_records(t)
    
    with tab3:
        show_delivery_records(t)
    
    with tab4:
        show_raw_receipts_records(t)


def show_production_records(t, df_raw, df_fg):
    """عرض سجلات الإنتاج مع فلاتر متقدمة"""
    st.subheader("📊 " + t["history_p"])
    
    # ==================== فلترة البيانات ====================
    with st.expander("🔍 " + t.get("filter_options", "Filter Options"), expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # فلتر التاريخ
            filter_date_range = st.checkbox(t.get("filter_by_date", "Filter by date"), key="prod_filter_date")
            if filter_date_range:
                start_date = st.date_input(
                    t.get("from_date", "From Date"),
                    datetime.now() - timedelta(days=30),
                    key="prod_start_date"
                )
                end_date = st.date_input(
                    t.get("to_date", "To Date"),
                    datetime.now(),
                    key="prod_end_date"
                )
            else:
                start_date = None
                end_date = None
        
        with col2:
            # فلتر المنتج
            products = db_manager.get_distinct_products()
            filter_product = st.checkbox(t.get("filter_by_product", "Filter by product"), key="prod_filter_product")
            if filter_product and products:
                selected_product = st.selectbox(t.get("col_product", "Product"), ["All"] + products, key="prod_product_select")
            else:
                selected_product = "All"
        
        with col3:
            # فلتر المشرف
            supervisors = db_manager.get_distinct_supervisors()
            filter_supervisor = st.checkbox(t.get("filter_by_supervisor", "Filter by supervisor"), key="prod_filter_supervisor")
            if filter_supervisor and supervisors:
                selected_supervisor = st.selectbox(t.get("col_supervisor", "Supervisor"), ["All"] + supervisors, key="prod_supervisor_select")
            else:
                selected_supervisor = "All"
        
        # فلتر الخط
        filter_line = st.checkbox(t.get("filter_by_line", "Filter by line"), key="prod_filter_line")
        if filter_line:
            line_options = [t.get("line1", "(line 1)"), t.get("line2", "(line 2)")]
            selected_line_filter = st.selectbox(t.get("col_line", "Line"), ["All"] + line_options, key="prod_line_select")
        else:
            selected_line_filter = "All"
    
    # جلب البيانات مع الفلاتر
    try:
        df_prod = db_manager.get_all_production(
            start_date=start_date,
            end_date=end_date,
            line=None if selected_line_filter == "All" else selected_line_filter,
            product=None if selected_product == "All" else selected_product,
            supervisor=None if selected_supervisor == "All" else selected_supervisor
        )
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")
        df_prod = pd.DataFrame()

    if df_prod is not None and not df_prod.empty:
        # تنسيق البيانات
        if "date" in df_prod.columns:
            df_prod["date"] = pd.to_datetime(df_prod["date"]).dt.strftime("%Y-%m-%d")
        
        if "operating_time" in df_prod.columns:
            df_prod["operating_hours"] = (pd.to_numeric(df_prod["operating_time"], errors="coerce").fillna(0) / 60).round(2)
        if "downtime_minutes" in df_prod.columns:
            df_prod["downtime_hours"] = (pd.to_numeric(df_prod["downtime_minutes"], errors="coerce").fillna(0) / 60).round(2)
        
        # عرض الجدول
        display_cols = ["id", "date", "line", "product", "output_units",
                        "preforms_used", "waste_bottles", "packaging_waste",
                        "line_speed", "efficiency", "operating_hours", "downtime_hours", "supervisor"]
        available_cols = [c for c in display_cols if c in df_prod.columns]
        labels = get_production_record_labels(t)
        display_df = df_prod[available_cols].copy()
        display_df = display_df.rename(columns={k: v for k, v in labels.items() if k in display_df.columns})
        
        st.dataframe(display_df, width='stretch')
        
        # إحصائيات
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(t.get("records_count", "عدد السجلات"), len(df_prod))
        with col2:
            total = df_prod["output_units"].sum() if "output_units" in df_prod.columns else 0
            st.metric(t.get("total_units", "إجمالي الإنتاج"), f"{total:,.0f}")
        with col3:
            avg_eff = df_prod["efficiency"].mean() if "efficiency" in df_prod.columns else 0
            st.metric(t.get("avg_efficiency", "متوسط الكفاءة"), f"{avg_eff:.1f}%")
        with col4:
            if "downtime_hours" in df_prod.columns:
                total_dt = df_prod["downtime_hours"].sum()
            elif "downtime_minutes" in df_prod.columns:
                total_dt = df_prod["downtime_minutes"].sum() / 60
            else:
                total_dt = 0
            st.metric(t.get("col_downtime", "مدة التوقف"), f"{total_dt:,.1f} {t.get('hours_word', 'ساعة')}")
        
        # زر تصدير Excel
        if st.button(t.get("export_excel", "📥 Export to Excel"), width='stretch'):
            export_df = df_prod[available_cols].copy()
            export_df.to_excel("production_export.xlsx", index=False)
            st.success("✅ تم التصدير إلى production_export.xlsx")
        
        st.markdown("---")
        _show_production_delete(df_prod, df_raw, df_fg, t)
    else:
        st.info("📭 " + t.get("no_production", "لا توجد سجلات إنتاج"))
        st.info("💡 " + t.get("tip_production", "قم بتسجيل تقرير إنتاج جديد من صفحة الإنتاج"))


def show_maintenance_records(t):
    """عرض سجلات الصيانة مع فلاتر متقدمة"""
    st.subheader("🔧 " + t["history_m"])
    
    # ==================== فلترة البيانات ====================
    with st.expander("🔍 " + t.get("filter_options", "Filter Options"), expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_date_range = st.checkbox(t.get("filter_by_date", "Filter by date"), key="maint_filter_date")
            if filter_date_range:
                start_date = st.date_input(t.get("from_date", "From Date"), datetime.now() - timedelta(days=30), key="maint_start_date")
                end_date = st.date_input(t.get("to_date", "To Date"), datetime.now(), key="maint_end_date")
            else:
                start_date = None
                end_date = None
        
        with col2:
            machines = db_manager.get_distinct_machines()
            filter_machine = st.checkbox(t.get("filter_by_machine", "Filter by machine"), key="maint_filter_machine")
            if filter_machine and machines:
                selected_machine = st.selectbox(t.get("col_machine", "Machine"), ["All"] + machines, key="maint_machine_select")
            else:
                selected_machine = "All"
        
        with col3:
            filter_type = st.checkbox(t.get("filter_by_type", "Filter by type"), key="maint_filter_type")
            if filter_type:
                type_options = ["planned", "breakdown"]
                selected_type = st.selectbox(t.get("col_type", "Type"), ["All"] + type_options, key="maint_type_select")
            else:
                selected_type = "All"
        
        filter_technician = st.checkbox(t.get("filter_by_technician", "Filter by technician"), key="maint_filter_tech")
        if filter_technician:
            technician = st.text_input(t.get("col_technician", "Technician"), key="maint_tech_input")
        else:
            technician = None
    
    try:
        df_maint = db_manager.get_all_maintenance(
            start_date=start_date,
            end_date=end_date,
            machine=None if selected_machine == "All" else selected_machine,
            maint_type=None if selected_type == "All" else selected_type,
            technician=technician
        )
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")
        df_maint = pd.DataFrame()

    if df_maint is not None and not df_maint.empty:
        display_cols = ["id", "date", "type", "line", "machine", "technician", "task", "issue", "spare_parts", "notes"]
        available_cols = [c for c in display_cols if c in df_maint.columns]
        rename_map = {
            "id": t.get("col_id", "رقم"),
            "date": t.get("col_date", "التاريخ"),
            "type": t.get("col_type", "النوع"),
            "line": t.get("col_line", "الخط"),
            "machine": t.get("col_machine", "الماكينة"),
            "technician": t.get("col_technician", "الفني"),
            "task": t.get("col_task", "المهمة"),
            "issue": t.get("col_issue", "العطل"),
            "spare_parts": t.get("maint_spare_parts_used", "قطع الغيار"),
            "notes": t.get("col_notes", "ملاحظات"),
        }
        display_df = df_maint[available_cols].copy()
        display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
        st.dataframe(display_df, width='stretch')
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(t.get("maint_records_count", "عدد السجلات"), len(df_maint))
        with col2:
            breakdown_count = len(df_maint[df_maint["type"] == "breakdown"]) if "type" in df_maint.columns else 0
            st.metric(t.get("records_breakdown_count", "⚠️ Breakdown Count"), breakdown_count)
        
        if st.button(t.get("export_excel", "📥 Export to Excel"), key="maint_export"):
            df_maint[available_cols].to_excel("maintenance_export.xlsx", index=False)
            st.success("✅ تم التصدير إلى maintenance_export.xlsx")
        
        st.markdown("---")
        _show_maintenance_delete(df_maint, t)
    else:
        st.info("📭 " + t.get("no_maintenance", "لا توجد سجلات صيانة"))
        st.info("💡 " + t.get("tip_maintenance", "قم بتسجيل تقرير صيانة جديد من صفحة الصيانة"))


def show_delivery_records(t):
    """عرض سجلات التحميل مع فلاتر متقدمة"""
    st.subheader("🚚 " + t["history_delivery"])
    
    # ==================== فلترة البيانات ====================
    with st.expander("🔍 " + t.get("filter_options", "Filter Options"), expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            filter_date_range = st.checkbox(t.get("filter_by_date", "Filter by date"), key="delivery_filter_date")
            if filter_date_range:
                start_date = st.date_input(t.get("from_date", "From Date"), datetime.now() - timedelta(days=30), key="delivery_start_date")
                end_date = st.date_input(t.get("to_date", "To Date"), datetime.now(), key="delivery_end_date")
            else:
                start_date = None
                end_date = None
        
        with col2:
            customers = db_manager.get_distinct_customers()
            filter_customer = st.checkbox(t.get("filter_by_customer", "Filter by customer"), key="delivery_filter_customer")
            if filter_customer and customers:
                selected_customer = st.selectbox(t.get("col_customer", "Customer"), ["All"] + customers, key="delivery_customer_select")
            else:
                selected_customer = "All"
        
        filter_product = st.checkbox(t.get("filter_by_product", "Filter by product"), key="delivery_filter_product")
        if filter_product:
            product = st.text_input(t.get("col_product", "Product"), key="delivery_product_input")
        else:
            product = None
    
    try:
        df_delivery = db_manager.get_all_delivery(
            start_date=start_date,
            end_date=end_date,
            product=product,
            customer=None if selected_customer == "All" else selected_customer
        )
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")
        df_delivery = pd.DataFrame()

    if df_delivery is not None and not df_delivery.empty:
        display_cols = ["id", "date", "product", "quantity", "customer", "delivery_note", "notes"]
        available_cols = [c for c in display_cols if c in df_delivery.columns]
        rename_map = {
            "id": t.get("col_id", "رقم"),
            "date": t.get("col_date", "التاريخ"),
            "product": t.get("col_product", "المنتج"),
            "quantity": t.get("col_qty", "الكمية"),
            "customer": t.get("col_customer", "العميل"),
            "delivery_note": "Delivery Note",
            "notes": t.get("col_notes", "ملاحظات"),
        }
        display_df = df_delivery[available_cols].copy()
        display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
        st.dataframe(display_df, width='stretch')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t.get("delivery_records_count", "عدد السجلات"), len(df_delivery))
        with col2:
            total_qty = df_delivery["quantity"].sum() if "quantity" in df_delivery.columns else 0
            st.metric(t.get("records_total_delivered", "Total Quantity Delivered"), f"{total_qty:,.0f}")
        with col3:
            unique_customers = df_delivery["customer"].nunique() if "customer" in df_delivery.columns else 0
            st.metric(t.get("records_customer_count", "Customer Count"), unique_customers)
        
        if st.button(t.get("export_excel", "📥 Export to Excel"), key="delivery_export"):
            df_delivery[available_cols].to_excel("delivery_export.xlsx", index=False)
            st.success("✅ تم التصدير إلى delivery_export.xlsx")
        
        st.markdown("---")
        _show_delivery_delete(df_delivery, t)
    else:
        st.info("📭 " + t.get("no_delivery_records", "لا توجد سجلات تسليم مسجلة"))


def show_raw_receipts_records(t):
    """عرض سجلات مشتريات المواد الخام مع فلاتر متقدمة"""
    st.subheader(t.get("records_raw_purchases_title", "📦 Raw Material Purchases"))
    
    # ==================== فلترة البيانات ====================
    with st.expander("🔍 " + t.get("filter_options", "Filter Options"), expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            filter_date_range = st.checkbox(t.get("filter_by_date", "Filter by date"), key="raw_filter_date")
            if filter_date_range:
                start_date = st.date_input(t.get("from_date", "From Date"), datetime.now() - timedelta(days=30), key="raw_start_date")
                end_date = st.date_input(t.get("to_date", "To Date"), datetime.now(), key="raw_end_date")
            else:
                start_date = None
                end_date = None
        
        with col2:
            filter_material = st.checkbox(t.get("filter_by_material", "Filter by material"), key="raw_filter_material")
            if filter_material:
                material = st.text_input(t.get("material", "Material"), key="raw_material_input")
            else:
                material = None
        
        filter_invoice = st.checkbox(t.get("filter_by_invoice", "Filter by invoice"), key="raw_filter_invoice")
        if filter_invoice:
            invoice = st.text_input(t.get("invoice", "Invoice"), key="raw_invoice_input")
        else:
            invoice = None
    
    try:
        df_raw_receipt = db_manager.get_all_raw_receipts(
            start_date=start_date,
            end_date=end_date,
            material=material,
            invoice=invoice
        )
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")
        df_raw_receipt = pd.DataFrame()

    if df_raw_receipt is not None and not df_raw_receipt.empty:
        display_cols = ["id", "date", "material", "quantity", "invoice", "notes"]
        available_cols = [c for c in display_cols if c in df_raw_receipt.columns]
        rename_map = {
            "id": t.get("col_id", "رقم"),
            "date": t.get("col_date", "التاريخ"),
            "material": t.get("material", "المادة"),
            "quantity": t.get("quantity", "الكمية"),
            "invoice": t.get("invoice", "رقم الفاتورة"),
            "notes": t.get("col_notes", "ملاحظات"),
        }
        display_df = df_raw_receipt[available_cols].copy()
        display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})
        st.dataframe(display_df, width='stretch')
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(t.get("records_count", "Records Count"), len(df_raw_receipt))
        with col2:
            total_qty = df_raw_receipt["quantity"].sum() if "quantity" in df_raw_receipt.columns else 0
            st.metric(t.get("records_total_received", "Total Quantity Received"), f"{total_qty:,.0f}")
        
        if st.button(t.get("export_excel", "📥 Export to Excel"), key="raw_export"):
            df_raw_receipt[available_cols].to_excel("raw_receipts_export.xlsx", index=False)
            st.success("✅ تم التصدير إلى raw_receipts_export.xlsx")
        
        st.markdown("---")
        _show_raw_receipt_delete(df_raw_receipt, t)
    else:
        st.info(t.get("records_no_raw_receipts", "📭 No raw material receipt records"))
        st.info(t.get("records_raw_receipts_hint", "💡 You can record raw material purchases from the Inventory page"))


# ============================================================================
# Delete Functions (نفس الكود القديم مع إضافة رسائل التأكيد)
# ============================================================================

def _show_production_delete(df_prod, df_raw, df_fg, t):
    """حذف سجل إنتاج مع إرجاع المخزون"""
    with st.expander("🗑️ " + t.get("delete_production_title", "حذف سجل إنتاج")):
        pw = st.text_input(t["password"], type="password", key="prod_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        df_display = df_prod.copy()
        if "date" in df_display.columns:
            df_display["_date_str"] = df_display["date"].astype(str)
        else:
            df_display["_date_str"] = ""

        df_display["desc"] = df_display.apply(
            lambda row: (
                f"ID:{row['id']} | {row.get('_date_str', '')} | "
                f"{row.get('line', '')} | {row.get('product', '')} | "
                f"{row.get('output_units', 0):,}"
            ),
            axis=1,
        )

        selected_desc = st.selectbox(
            t.get("select_record_delete", "اختر السجل للحذف"),
            options=df_display["desc"].tolist(),
            key="prod_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        st.caption("ℹ️ " + t.get("records_delete_restore_hint", "الحذف يُرجع المواد الخام ويخصم المنتج التام"))

        if st.button("🗑️ " + t.get("delete_confirm", "حذف"), key="prod_del_btn", type="primary"):
            # ✅ حذف شرط كتابة DELETE
            ok, msg = delete_production_record(selected_id, None, None)
            if ok:
                st.success(t.get("delete_success", "تم الحذف") + f" — {msg}")
                st.cache_data.clear()
                st.session_state.inventory_version = st.session_state.get('inventory_version', 0) + 1
                st.rerun()
            else:
                st.error(t.get("delete_failed", "فشل الحذف") + f": {msg}")


def _show_maintenance_delete(df_maint, t):
    """حذف سجل صيانة (بدون تأثير على المخزون)"""
    with st.expander(t.get("records_delete_maint_title", "🗑️ Delete Maintenance Record")):
        pw = st.text_input(t["password"], type="password", key="maint_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        df_display = df_maint.copy()
        if "date" in df_display.columns:
            df_display["_date_str"] = pd.to_datetime(df_display["date"]).dt.strftime("%Y-%m-%d")
        else:
            df_display["_date_str"] = ""

        df_display["desc"] = df_display.apply(
            lambda row: (
                f"ID:{row['id']} | {row.get('_date_str', '')} | "
                f"{row.get('machine', '')} | {row.get('type', '')} | "
                f"{row.get('technician', '')}"
            ),
            axis=1,
        )

        selected_desc = st.selectbox(
            t.get("select_record_delete", "اختر السجل للحذف"),
            options=df_display["desc"].tolist(),
            key="maint_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        selected_row = df_maint[df_maint["id"] == selected_id].iloc[0]
        st.info(f"{t.get('records_record_details', '📋 **Record Details:**')} {t.get('col_machine', 'Machine')}: {selected_row.get('machine', 'N/A')} | {t.get('col_date', 'Date')}: {selected_row.get('_date_str', 'N/A')}")

        if st.button(t.get("records_confirm_delete_maint", "🗑️ Confirm Delete Maintenance Record"), key="maint_del_btn", type="primary"):
            confirm = st.text_input(t.get("confirm_delete", "Type 'DELETE' to confirm"), key="maint_confirm")
            if confirm == "DELETE":
                if delete_maintenance_record(selected_id):
                    st.success(f"{t.get('records_maint_deleted', '✅ Maintenance record deleted successfully')} {selected_id}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"{t.get('records_maint_delete_failed', '❌ Failed to delete maintenance record')} {selected_id}")
            else:
                st.error(t.get("confirm_delete_error", "Please type 'DELETE' to confirm"))


def _show_delivery_delete(df_delivery, t):
    """حذف سجل تحميل (بدون تأثير على المخزون)"""
    with st.expander(t.get("records_delete_delivery_title", "🗑️ Delete Delivery Record")):
        pw = st.text_input(t["password"], type="password", key="delivery_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        df_display = df_delivery.copy()
        if "date" in df_display.columns:
            df_display["_date_str"] = pd.to_datetime(df_display["date"]).dt.strftime("%Y-%m-%d")
        else:
            df_display["_date_str"] = ""

        df_display["desc"] = df_display.apply(
            lambda row: (
                f"ID:{row['id']} | {row.get('_date_str', '')} | "
                f"{row.get('product', '')} | {row.get('quantity', 0):,} | "
                f"{row.get('customer', '')}"
            ),
            axis=1,
        )

        selected_desc = st.selectbox(
            t.get("select_record_delete", "اختر السجل للحذف"),
            options=df_display["desc"].tolist(),
            key="delivery_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        if st.button(t.get("records_confirm_delete_delivery", "🗑️ Confirm Delete Delivery Record"), key="delivery_del_btn", type="primary"):
            confirm = st.text_input(t.get("confirm_delete", "Type 'DELETE' to confirm"), key="delivery_confirm")
            if confirm == "DELETE":
                if delete_delivery_record(selected_id):
                    st.success(f"{t.get('records_delivery_deleted', '✅ Delivery record deleted successfully')} {selected_id}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"{t.get('records_delivery_delete_failed', '❌ Failed to delete delivery record')} {selected_id}")
            else:
                st.error(t.get("confirm_delete_error", "Please type 'DELETE' to confirm"))


def _show_raw_receipt_delete(df_raw_receipt, t):
    """حذف سجل مشتريات مواد خام (بدون تأثير على المخزون)"""
    with st.expander(t.get("records_delete_receipt_title", "🗑️ Delete Purchase Record")):
        pw = st.text_input(t["password"], type="password", key="raw_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        df_display = df_raw_receipt.copy()
        if "date" in df_display.columns:
            df_display["_date_str"] = pd.to_datetime(df_display["date"]).dt.strftime("%Y-%m-%d")
        else:
            df_display["_date_str"] = ""

        df_display["desc"] = df_display.apply(
            lambda row: (
                f"ID:{row['id']} | {row.get('_date_str', '')} | "
                f"{row.get('material', '')} | {row.get('quantity', 0):,} | "
                f"فاتورة: {row.get('invoice', '')}"
            ),
            axis=1,
        )

        selected_desc = st.selectbox(
            t.get("select_record_delete", "اختر السجل للحذف"),
            options=df_display["desc"].tolist(),
            key="raw_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        if st.button(t.get("records_confirm_delete_receipt", "🗑️ Confirm Delete Purchase Record"), key="raw_del_btn", type="primary"):
            confirm = st.text_input(t.get("confirm_delete", "Type 'DELETE' to confirm"), key="raw_confirm")
            if confirm == "DELETE":
                if delete_raw_receipt_record(selected_id):
                    st.success(f"{t.get('records_receipt_deleted', '✅ Purchase record deleted successfully')} {selected_id}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"{t.get('records_receipt_delete_failed', '❌ Failed to delete purchase record')} {selected_id}")
            else:
                st.error(t.get("confirm_delete_error", "Please type 'DELETE' to confirm"))