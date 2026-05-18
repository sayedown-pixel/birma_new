import streamlit as st
import pandas as pd
from datetime import datetime
from database import db_manager
from inventory import update_raw_materials, update_finished_goods
from utils import (
    CONFIG,
    consume_materials,
    add_to_finished_goods,
    send_telegram,
    get_bom_unit_info,
    calculate_production_metrics,
)


def show_production(selected_line, df_raw, df_fg, t):
    st.header(f"{t.get('production', 'Production')} - {selected_line}")

    with st.expander("📋 " + t.get("raw_stock_expander", "Raw stock"), expanded=False):
        if df_raw is not None and not df_raw.empty:
            display_cols = []
            for col in ["Material_Name_AR", "Material_Name", "Name"]:
                if col in df_raw.columns:
                    display_cols.append(col)
                    break
            for col in ["Current_Stock", "Stock"]:
                if col in df_raw.columns:
                    display_cols.append(col)
                    break
            if display_cols:
                st.dataframe(df_raw[display_cols], use_container_width=True)
            else:
                st.dataframe(df_raw, use_container_width=True)
        else:
            st.warning("⚠️ " + t.get("no_raw_stock", "No stock data"))

    st.caption("ℹ️ " + t.get("unit_hint", ""))

    with st.form("prod_form"):
        st.subheader("📝 " + t.get("prod_report_title", "Production report"))

        col1, col2 = st.columns(2)
        with col1:
            supervisor = st.text_input(
                t["sup_label"],
                value=st.session_state.get("user_name", ""),
            )
            product = st.selectbox(t["prod_label"], CONFIG[selected_line]["products"])
            bom = get_bom_unit_info(product)
            st.caption(
                f"📦 {bom['pieces_per_unit']} "
                + ("عبوة/وحدة" if st.session_state.get("lang") != "en" else "pcs/unit")
            )

            # تهيئة القيم الافتراضية في session_state
            if "prod_target" not in st.session_state:
                st.session_state.prod_target = 100
            if "prod_preforms" not in st.session_state:
                st.session_state.prod_preforms = st.session_state.prod_target * bom["pieces_per_unit"]
            if "prod_packaging" not in st.session_state:
                st.session_state.prod_packaging = st.session_state.prod_target

            target = st.number_input(
                t.get("prod_qty_units", "Quantity (units)"),
                min_value=0,
                step=1,
                value=st.session_state.prod_target,
                key="prod_target",
            )
            # حساب البريفورم المتوقع تلقائياً
            expected_preforms = target * bom["pieces_per_unit"]
            preforms_used = st.number_input(
                t.get("preform_actual", "Preforms / bottles used (total)"),
                min_value=0,
                step=bom["pieces_per_unit"],
                value=expected_preforms,
                help=f"المتوقع: {expected_preforms:,} (الكمية × {bom['pieces_per_unit']} عبوة/وحدة)",
                key="prod_preforms",
            )
            pack_label = (
                t.get("packaging_carton", "Packaging units (cartons)")
                if "Carton" in product
                else t.get("packaging_shrink", "Packaging units (shrink)")
            )
            packaging_used = st.number_input(
                pack_label,
                min_value=0,
                step=1,
                value=target,
                help=t.get("packaging_help", "0 = same as production units"),
                key="prod_packaging",
            )
            st.markdown("**⏰ " + t.get("shift_info", "Shift") + "**")
            shift_start = st.time_input(
                t.get("shift_start", "Shift start"),
                value=datetime.strptime("08:00", "%H:%M").time(),
            )
            shift_end = st.time_input(
                t.get("shift_end", "Shift end"),
                value=datetime.strptime("02:00", "%H:%M").time(),
            )
            break_minutes = st.number_input(
                t.get("break_minutes_label", "Break (minutes)"),
                min_value=0,
                max_value=240,
                value=180,
                step=15,
            )

        with col2:
            prod_date = st.date_input(t["date_label"], datetime.now())
            speed = CONFIG[selected_line]["speed"][product]
            st.info(
                f"⚡ {t.get('line_speed_label', 'Line speed')}: "
                f"{speed:,} {t.get('bottles_per_hour', 'bottles/hr')}"
            )

            # ── معاينة الحسابات الفورية ─────────────────────────
            if target > 0:
                _bom     = get_bom_unit_info(product)
                _ppu     = max(1, _bom["pieces_per_unit"])
                _good    = int(target) * _ppu
                _pfused  = int(preforms_used) if int(preforms_used) > 0 else _good
                _waste_b = max(0, _pfused - _good)

                # حساب وقت التشغيل
                try:
                    _s = shift_start.hour * 60 + shift_start.minute
                    _e = shift_end.hour   * 60 + shift_end.minute
                    if _e <= _s:
                        _e += 24 * 60
                    _wmin  = max(0, (_e - _s) - int(break_minutes))
                    _whr   = _wmin / 60.0
                    _theo  = speed * _whr
                    _eff   = round((_pfused / _theo * 100), 1) if _theo > 0 else 0.0
                    _eff   = min(100.0, _eff)
                    _req_h = _pfused / speed if speed > 0 else 0
                    _dt_h  = max(0.0, _whr - _req_h)
                    _dt_m  = int(round(_dt_h * 60))
                except Exception:
                    _eff, _dt_m, _wmin, _theo = 0.0, 0, 0, 0

                _pkused  = int(packaging_used) if int(packaging_used) > 0 else int(target)
                _pk_waste = max(0, _pkused - int(target))

                st.markdown("---")
                st.markdown("**📊 معاينة الحسابات:**")
                _c1, _c2 = st.columns(2)
                with _c1:
                    st.metric("🍶 عبوات جيدة",   f"{_good:,}")
                    st.metric("🗑️ هالك عبوات",   f"{_waste_b:,}")
                    st.metric("⏱️ توقف متوقع",   f"{_dt_m} د")
                with _c2:
                    st.metric("📈 الكفاءة",       f"{_eff}%")
                    st.metric("📦 هالك تغليف",    f"{_pk_waste} وحدة")
                    st.metric("🕐 وقت تشغيل",    f"{round(_wmin/60,1)} س")

        submitted = st.form_submit_button(
            "💾 " + t.get("save_report", "Save"),
            use_container_width=True,
        )

        if submitted:
            lang_en = st.session_state.get("lang") == "en"
            if target <= 0:
                st.error(
                    "⚠️ "
                    + ("Quantity must be > 0" if lang_en else "الكمية يجب أن تكون أكبر من صفر")
                )
            elif not supervisor:
                st.error(
                    "⚠️ "
                    + ("Enter supervisor name" if lang_en else "يرجى إدخال اسم المشرف")
                )
            else:
                metrics = calculate_production_metrics(
                    product,
                    target,
                    shift_start,
                    shift_end,
                    break_minutes,
                    speed,
                    preforms_used,
                    packaging_used,
                )

                packaging_unit = "شرنك" if "Shrink" in product else "كرتون"

                new_raw, raw_ok, raw_msg = consume_materials(product, target, df_raw)
                if not raw_ok:
                    st.error(f"❌ {raw_msg}")
                elif not update_raw_materials(new_raw):
                    st.error(
                        "❌ "
                        + ("Failed to update inventory" if lang_en else "فشل تحديث المخزون")
                    )
                else:
                    pieces = metrics["pieces_per_unit"]
                    production_data = {
                        "date": str(prod_date),
                        "line": selected_line,
                        "supervisor": supervisor,
                        "product": product,
                        "output_units": int(target),
                        "preforms_used": int(preforms_used),
                        "packaging_used": metrics["final_packaging"],
                        "packaging_unit": packaging_unit,
                        "waste_bottles": metrics["waste_bottles"],
                        "packaging_waste": metrics["packaging_waste"],
                        "line_speed": metrics["line_speed"],
                        "efficiency": float(metrics["efficiency"]),
                        "downtime_minutes": metrics["downtime_minutes"],
                        "working_minutes": metrics["working_minutes"],
                        "pieces_per_unit": pieces,
                        "ideal_run_rate": metrics["ideal_run_rate"],
                        "shift_start": shift_start.strftime("%H:%M"),
                        "shift_end": shift_end.strftime("%H:%M"),
                        "break_minutes": int(break_minutes),
                    }
                    try:
                        record_id = db_manager.save_production(production_data)
                        st.success(
                            f"✅ {t.get('report_saved', 'Saved')}! "
                            f"{t.get('record_no', 'ID')}: {record_id}"
                        )
                        new_fg, fg_ok, fg_msg = add_to_finished_goods(product, target, df_fg)
                        if fg_ok and new_fg is not None:
                            update_finished_goods(new_fg)
                            st.success(fg_msg)
                        try:
                            send_telegram(
                                f"🚀 {selected_line} - {product}: {target:,} "
                                f"{t.get('units_word', 'units')} | "
                                f"Eff: {metrics['efficiency']}% | "
                                f"DT: {metrics['downtime_hours']}h"
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"❌ {e}")
