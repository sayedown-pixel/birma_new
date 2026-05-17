import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import db_manager
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
        st.subheader("📊 " + t["history_p"])
        st.caption("📅 " + t.get("last_10_days", "Last 10 days"))
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
                    st.metric(t.get("records_count", "Records"), len(df_prod))
                with col2:
                    total = df_prod["output_units"].sum() if "output_units" in df_prod.columns else 0
                    st.metric(t.get("total_units", "Total"), f"{total:,.0f}")
                with col3:
                    avg_eff = df_prod["efficiency"].mean() if "efficiency" in df_prod.columns else 0
                    st.metric(t.get("avg_efficiency", "Avg Eff."), f"{avg_eff:.1f}%")
                with col4:
                    if "downtime_hours" in df_prod.columns:
                        total_dt = df_prod["downtime_hours"].sum()
                    elif "downtime_minutes" in df_prod.columns:
                        total_dt = df_prod["downtime_minutes"].sum() / 60
                    else:
                        total_dt = 0
                    st.metric(
                        t.get("col_downtime", "Downtime"),
                        f"{total_dt:,.1f} {t.get('hours_word', 'hrs')}",
                    )

                st.markdown("---")
                _show_production_delete(df_prod, df_raw, df_fg, t)
            else:
                st.info("📭 " + t.get("no_production", "No records"))
                st.info("💡 " + t.get("tip_production", ""))

        except Exception as e:
            st.error(f"❌ {e}")

    with tab2:
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
                    "id": t.get("col_id", "ID"),
                    "date": t.get("col_date", "Date"),
                    "type": t.get("col_type", "Type"),
                    "line": t.get("col_line", "Line"),
                    "machine": t.get("col_machine", "Machine"),
                    "technician": t.get("col_technician", "Technician"),
                    "task": t.get("col_task", "Task"),
                    "issue": t.get("col_issue", "Issue"),
                    "spare_parts": "قطع الغيار",
                    "notes": t.get("col_notes", "Notes"),
                }
                display_df = df_maint[available_cols].copy()
                display_df = display_df.rename(
                    columns={k: v for k, v in rename_map.items() if k in display_df.columns}
                )
                st.dataframe(display_df, use_container_width=True)
                st.metric(t.get("maint_records_count", "Count"), len(df_maint))
            else:
                st.info("📭 " + t.get("no_maintenance", "No records"))
                st.info("💡 " + t.get("tip_maintenance", ""))

        except Exception as e:
            st.error(f"❌ {e}")

    with tab3:
        st.subheader("🚚 " + t["history_delivery"])
        try:
            df_delivery = db_manager.get_all_delivery()

            if df_delivery is not None and not df_delivery.empty:
                display_cols = ["id", "date", "product", "quantity", "customer", "delivery_note", "notes"]
                available_cols = [c for c in display_cols if c in df_delivery.columns]
                rename_map = {
                    "id": t.get("col_id", "ID"),
                    "date": t.get("col_date", "Date"),
                    "product": t.get("col_product", "Product"),
                    "quantity": t.get("col_qty", "Qty"),
                    "customer": t.get("col_customer", "Customer"),
                    "delivery_note": "رقم سند التحميل",
                    "notes": t.get("col_notes", "Notes"),
                }
                display_df = df_delivery[available_cols].copy()
                display_df = display_df.rename(
                    columns={k: v for k, v in rename_map.items() if k in display_df.columns}
                )
                st.dataframe(display_df, use_container_width=True)
                st.metric(t.get("delivery_records_count", "Count"), len(df_delivery))
            else:
                st.info("📭 " + t.get("no_delivery_records", "No delivery records"))

        except Exception as e:
            st.error(f"❌ {e}")

    with tab4:
        st.subheader("📦 سجل مشتريات المواد الخام")
        try:
            df_raw_receipt = db_manager.get_all_raw_receipts()

            if df_raw_receipt is not None and not df_raw_receipt.empty:
                display_cols = ["id", "date", "material", "quantity", "invoice", "notes"]
                available_cols = [c for c in display_cols if c in df_raw_receipt.columns]
                rename_map = {
                    "id": t.get("col_id", "ID"),
                    "date": t.get("col_date", "Date"),
                    "material": t.get("material", "Material"),
                    "quantity": t.get("quantity", "Qty"),
                    "invoice": t.get("invoice", "Invoice"),
                    "notes": t.get("col_notes", "Notes"),
                }
                display_df = df_raw_receipt[available_cols].copy()
                display_df = display_df.rename(
                    columns={k: v for k, v in rename_map.items() if k in display_df.columns}
                )
                st.dataframe(display_df, use_container_width=True)
                st.metric("عدد السجلات", len(df_raw_receipt))

                if "quantity" in df_raw_receipt.columns:
                    total_qty = df_raw_receipt["quantity"].sum()
                    st.metric("إجمالي الكميات", f"{total_qty:,.0f}")
            else:
                st.info("📭 لا توجد سجلات مشتريات مواد خام")
                st.info("💡 يمكنك تسجيل مشتريات المواد الخام من صفحة المخازن")

        except Exception as e:
            st.error(f"❌ {e}")


def _show_production_delete(df_prod, df_raw, df_fg, t):
    """Manual delete with inventory restore."""
    with st.expander("🗑️ " + t.get("delete_production_title", "Delete production record")):
        pw = st.text_input(t["password"], type="password", key="records_del_pw")
        if pw not in ["admin123", "100"]:
            if pw:
                st.warning("🔒 " + t.get("login_error", "Wrong password"))
            else:
                st.warning("🔒 " + t.get("admin_title", "Admin password required"))
            return

        if df_raw is None or df_raw.empty:
            st.error("⚠️ " + t.get("no_raw_stock", "No raw materials data"))
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
            t.get("select_record_delete", "Select record"),
            options=df_display["desc"].tolist(),
            key="records_del_select",
        )
        selected_id = int(selected_desc.split("|")[0].replace("ID:", "").strip())

        st.caption(
            "ℹ️ "
            + (
                "Deleting restores raw materials and finished goods to inventory."
                if st.session_state.get("lang") == "en"
                else "الحذف يُرجع المواد الخام والمنتج التام إلى المخازن تلقائياً."
            )
        )

        if st.button("🗑️ " + t.get("delete_confirm", "Delete"), key="records_del_btn", type="primary"):
            ok, msg = delete_production_record(selected_id, df_raw, df_fg)
            if ok:
                st.success(t.get("delete_success", "Deleted") + f" — {msg}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(t.get("delete_failed", "Failed") + f": {msg}")
