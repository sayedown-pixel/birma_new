import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import db_manager, delete_maintenance_record, delete_delivery_record, delete_raw_receipt_record
from utils import get_production_record_labels, delete_production_record


def show_records(t, lang, df_raw=None, df_fg=None):
    """Display records page with tabs for different record types"""
    st.header(t["records"])

    tab1, tab2, tab3, tab4 = st.tabs([
        t["history_p"],
        t["history_m"],
        t["history_delivery"],
        "📦 سجل مشتريات المواد الخام",
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
    """عرض سجلات الإنتاج مع إمكانية الحذف"""
    st.subheader("📊 " + t["history_p"])
    st.caption("📅 " + t.get("last_10_days", "آخر 10 أيام"))
    
    try:
        start_date = datetime.now() - timedelta(days=10)
        df_prod = db_manager.get_all_production(start_date=start_date)

        if df_prod is not None and not df_prod.empty:
            if "date" in df_prod.columns:
                df_prod["date"] = pd.to_datetime(df_prod["date"]).dt.strftime("%Y-%m-%d")

            if "operating_time" in df_prod.columns:
                df_prod["operating_hours"] = (
                    pd.to_numeric(df_prod["operating_time"], errors="coerce").fillna(0) / 60
                ).round(2)
            if "downtime_minutes" in df_prod.columns:
                df_prod["downtime_hours"] = (
                    pd.to_numeric(df_prod["downtime_minutes"], errors="coerce").fillna(0) / 60
                ).round(2)

            display_cols = [
                "id", "date", "line", "product", "output_units",
                "preforms_used", "waste_bottles", "packaging_waste",
                "line_speed", "efficiency",
                "operating_hours", "downtime_hours", "supervisor",
            ]
            available_cols = [c for c in display_cols if c in df_prod.columns]
            labels = get_production_record_labels(t)
            display_df = df_prod[available_cols].copy()
            display_df = display_df.rename(
                columns={k: v for k, v in labels.items() if k in display_df.columns}
            )
            st.dataframe(display_df, use_container_width=True)

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

            st.markdown("---")
            _show_production_delete(df_prod, df_raw, df_fg, t)
        else:
            st.info("📭 " + t.get("no_production", "لا توجد سجلات إنتاج"))
            st.info("💡 " + t.get("tip_production", "قم بتسجيل تقرير إنتاج جديد من صفحة الإنتاج"))

    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")


def show_maintenance_records(t):
    """عرض سجلات الصيانة مع إمكانية الحذف"""
    st.subheader("🔧 " + t["history_m"])
    
    try:
        df_maint = db_manager.get_all_maintenance()

        if df_maint is not None and not df_maint.empty:
            display_cols = [
                "id", "date", "type", "line", "machine",
                "technician", "task", "issue", "spare_parts", "notes",
            ]
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
                "spare_parts": "قطع الغيار",
                "notes": t.get("col_notes", "ملاحظات"),
            }
            display_df = df_maint[available_cols].copy()
            display_df = display_df.rename(
                columns={k: v for k, v in rename_map.items() if k in display_df.columns}
            )
            st.dataframe(display_df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(t.get("maint_records_count", "عدد السجلات"), len(df_maint))
            with col2:
                breakdown_count = len(df_maint[df_maint["type"] == "breakdown"]) if "type" in df_maint.columns else 0
                st.metric("⚠️ عدد الأعطال", breakdown_count)
            
            st.markdown("---")
            _show_maintenance_delete(df_maint, t)
        else:
            st.info("📭 " + t.get("no_maintenance", "لا توجد سجلات صيانة"))
            st.info("💡 " + t.get("tip_maintenance", "قم بتسجيل تقرير صيانة جديد من صفحة الصيانة"))

    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")


def show_delivery_records(t):
    """عرض سجلات التحميل مع إمكانية الحذف"""
    st.subheader("🚚 " + t["history_delivery"])
    
    try:
        df_delivery = db_manager.get_all_delivery()

        if df_delivery is not None and not df_delivery.empty:
            display_cols = ["id", "date", "product", "quantity", "customer", "delivery_note", "notes"]
            available_cols = [c for c in display_cols if c in df_delivery.columns]
            rename_map = {
                "id": t.get("col_id", "رقم"),
                "date": t.get("col_date", "التاريخ"),
                "product": t.get("col_product", "المنتج"),
                "quantity": t.get("col_qty", "الكمية"),
                "customer": t.get("col_customer", "العميل"),
                "delivery_note": "رقم سند التحميل",
                "notes": t.get("col_notes", "ملاحظات"),
            }
            display_df = df_delivery[available_cols].copy()
            display_df = display_df.rename(
                columns={k: v for k, v in rename_map.items() if k in display_df.columns}
            )
            st.dataframe(display_df, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(t.get("delivery_records_count", "عدد السجلات"), len(df_delivery))
            with col2:
                total_qty = df_delivery["quantity"].sum() if "quantity" in df_delivery.columns else 0
                st.metric("إجمالي الكميات المسلمة", f"{total_qty:,.0f}")
            with col3:
                unique_customers = df_delivery["customer"].nunique() if "customer" in df_delivery.columns else 0
                st.metric("عدد العملاء", unique_customers)
            
            st.markdown("---")
            _show_delivery_delete(df_delivery, t)
        else:
            st.info("📭 " + t.get("no_delivery_records", "لا توجد سجلات تسليم مسجلة"))

    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")


def show_raw_receipts_records(t):
    """عرض سجلات مشتريات المواد الخام مع إمكانية الحذف"""
    st.subheader("📦 سجل مشتريات المواد الخام")
    
    try:
        df_raw_receipt = db_manager.get_all_raw_receipts()

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
            display_df = display_df.rename(
                columns={k: v for k, v in rename_map.items() if k in display_df.columns}
            )
            st.dataframe(display_df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("عدد السجلات", len(df_raw_receipt))
            with col2:
                total_qty = df_raw_receipt["quantity"].sum() if "quantity" in df_raw_receipt.columns else 0
                st.metric("إجمالي الكميات المستلمة", f"{total_qty:,.0f}")
            
            st.markdown("---")
            _show_raw_receipt_delete(df_raw_receipt, t)
        else:
            st.info("📭 لا توجد سجلات مشتريات مواد خام")
            st.info("💡 يمكنك تسجيل مشتريات المواد الخام من صفحة المخازن")

    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")


# ============================================================================
# Delete Functions for Each Record Type
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

        if df_raw is None or df_raw.empty:
            st.error("⚠️ " + t.get("no_raw_stock", "لا توجد بيانات مواد خام"))
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

        st.caption(
            "ℹ️ " + "الحذف يُرجع المواد الخام والمنتج التام إلى المخازن تلقائياً."
        )

        if st.button("🗑️ " + t.get("delete_confirm", "حذف"), key="prod_del_btn", type="primary"):
            ok, msg = delete_production_record(selected_id, df_raw, df_fg)
            if ok:
                st.success(t.get("delete_success", "تم الحذف") + f" — {msg}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(t.get("delete_failed", "فشل الحذف") + f": {msg}")


def _show_maintenance_delete(df_maint, t):
    """حذف سجل صيانة (بدون تأثير على المخزون)"""
    with st.expander("🗑️ حذف سجل صيانة"):
        pw = st.text_input(t["password"], type="password", key="maint_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        # تحضير قائمة السجلات للاختيار
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
            "اختر سجل الصيانة للحذف",
            options=df_display["desc"].tolist(),
            key="maint_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        # عرض تفاصيل السجل قبل الحذف
        selected_row = df_maint[df_maint["id"] == selected_id].iloc[0]
        st.info(f"📋 **تفاصيل السجل:** ماكينة: {selected_row.get('machine', 'N/A')} | التاريخ: {selected_row.get('_date_str', 'N/A')} | النوع: {selected_row.get('type', 'N/A')}")

        st.caption("ℹ️ " + "حذف سجل الصيانة لا يؤثر على المخزون أو الإنتاج.")

        if st.button("🗑️ تأكيد حذف سجل الصيانة", key="maint_del_btn", type="primary"):
            if delete_maintenance_record(selected_id):
                st.success(f"✅ تم حذف سجل الصيانة رقم {selected_id} بنجاح")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ فشل حذف سجل الصيانة رقم {selected_id}")


def _show_delivery_delete(df_delivery, t):
    """حذف سجل تحميل (بدون تأثير على المخزون)"""
    with st.expander("🗑️ حذف سجل تحميل"):
        pw = st.text_input(t["password"], type="password", key="delivery_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        # تحضير قائمة السجلات للاختيار
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
            "اختر سجل التحميل للحذف",
            options=df_display["desc"].tolist(),
            key="delivery_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        # عرض تفاصيل السجل قبل الحذف
        selected_row = df_delivery[df_delivery["id"] == selected_id].iloc[0]
        st.info(f"📋 **تفاصيل السجل:** المنتج: {selected_row.get('product', 'N/A')} | الكمية: {selected_row.get('quantity', 0):,} | العميل: {selected_row.get('customer', 'N/A')}")

        st.caption("ℹ️ " + "حذف سجل التحميل لا يؤثر على رصيد المخزون (يُنصح بتعديل الرصيد يدوياً إذا لزم الأمر).")

        if st.button("🗑️ تأكيد حذف سجل التحميل", key="delivery_del_btn", type="primary"):
            if delete_delivery_record(selected_id):
                st.success(f"✅ تم حذف سجل التحميل رقم {selected_id} بنجاح")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ فشل حذف سجل التحميل رقم {selected_id}")


def _show_raw_receipt_delete(df_raw_receipt, t):
    """حذف سجل مشتريات مواد خام (بدون تأثير على المخزون)"""
    with st.expander("🗑️ حذف سجل مشتريات مواد خام"):
        pw = st.text_input(t["password"], type="password", key="raw_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "كلمة المرور غير صحيحة"))
            else:
                st.warning("🔒 " + t.get("admin_title", "مطلوب كلمة مرور المشرف"))
            return

        # تحضير قائمة السجلات للاختيار
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
            "اختر سجل المشتريات للحذف",
            options=df_display["desc"].tolist(),
            key="raw_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        # عرض تفاصيل السجل قبل الحذف
        selected_row = df_raw_receipt[df_raw_receipt["id"] == selected_id].iloc[0]
        st.info(f"📋 **تفاصيل السجل:** المادة: {selected_row.get('material', 'N/A')} | الكمية: {selected_row.get('quantity', 0):,} | الفاتورة: {selected_row.get('invoice', 'N/A')}")

        st.caption("ℹ️ " + "حذف سجل المشتريات لا يؤثر على رصيد المخزون (يُنصح بتعديل الرصيد يدوياً إذا لزم الأمر).")

        if st.button("🗑️ تأكيد حذف سجل المشتريات", key="raw_del_btn", type="primary"):
            if delete_raw_receipt_record(selected_id):
                st.success(f"✅ تم حذف سجل المشتريات رقم {selected_id} بنجاح")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ فشل حذف سجل المشتريات رقم {selected_id}")