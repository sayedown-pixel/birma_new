# production.py - الكود الكامل والصحيح

import streamlit as st
import pandas as pd
from datetime import datetime
from database import db_manager
from inventory import update_raw_materials, update_finished_goods
from inventory_db import consume_materials_db, add_to_finished_goods_db
from constants import CONFIG
from helpers import (
    calculate_production_metrics,
    get_bom_unit_info,
    send_telegram
)
from utils import load_language
from helpers import clean_line_name

def show_production(selected_line, df_raw, df_fg, t):
    from helpers import normalize_line_name
    # ✅ تحويل اسم الخط للعرض
    line_display = normalize_line_name(selected_line)
    st.header(f"{t.get('production', 'Production')} - {line_display}")
    # تهيئة متغيرات session_state
    if "prod_target" not in st.session_state:
        st.session_state.prod_target = 100
    if "prod_preforms" not in st.session_state:
        st.session_state.prod_preforms = 100
    if "prod_packaging" not in st.session_state:
        st.session_state.prod_packaging = 100

    current_lang = st.session_state.get('lang', 'ar')
    
    # تحديد عمود اسم المادة حسب اللغة
    material_name_col = 'Material_Name_AR'
    if current_lang == 'en' and df_raw is not None and 'Material_Name_EN' in df_raw.columns:
        material_name_col = 'Material_Name_EN'
    elif current_lang == 'ar' and df_raw is not None and 'Material_Name_AR' in df_raw.columns:
        material_name_col = 'Material_Name_AR'
    elif df_raw is not None:
        for col in ['Material_Name_AR', 'Material_Name_EN', 'Material_Name', 'Name']:
            if col in df_raw.columns:
                material_name_col = col
                break
    
    stock_col = 'Current_Stock' if df_raw is not None and 'Current_Stock' in df_raw.columns else 'Stock'
    if stock_col not in (df_raw.columns if df_raw is not None else []):
        stock_col = None

    with st.expander("📋 " + t.get("raw_stock_expander", "Raw stock"), expanded=False):
        if df_raw is not None and not df_raw.empty:
            display_cols = []
            if material_name_col in df_raw.columns:
                display_cols.append(material_name_col)
            if stock_col and stock_col in df_raw.columns:
                display_cols.append(stock_col)
            if display_cols:
                st.dataframe(df_raw[display_cols], width='stretch')
            else:
                st.dataframe(df_raw, width='stretch')
        else:
            st.warning("⚠️ " + t.get("no_raw_stock", "No stock data"))

    st.caption("ℹ️ " + t.get("unit_hint", ""))

    with st.form("prod_form"):
        st.subheader("📝 " + t.get("prod_report_title", "Production report"))

        col1, col2 = st.columns(2)
        with col1:
            supervisor = st.text_input(
                t["sup_label"],
                value="",
                placeholder=t.get("enter_supervisor_name", "أدخل اسم المشرف"),
                key="supervisor_input"
            )
            product = st.selectbox(
                t["prod_label"], 
                CONFIG[selected_line]["products"],
                key="product_select"
            )
            bom = get_bom_unit_info(product)
            st.caption(f"📦 {bom['pieces_per_unit']} {t.get('pcs_per_unit', 'pcs/unit')}")

            target = st.number_input(
                t.get("prod_qty_units", "Quantity (units)"),
                min_value=0,
                step=1,
                value=st.session_state.prod_target,
                key="prod_target_input"
            )
            st.session_state.prod_target = target
            
            expected_preforms = target * bom["pieces_per_unit"]
            preforms_used = st.number_input(
                t.get("preform_actual", "Preforms / bottles used (total)"),
                min_value=0,
                step=bom["pieces_per_unit"],
                value=st.session_state.prod_preforms,
                help=t.get('preform_help', 'Required — saved in records exactly as entered'),
                key="preforms_used_input"
            )
            st.session_state.prod_preforms = preforms_used
            
            pack_label = (
                t.get("packaging_carton", "Packaging units (cartons)")
                if "Carton" in product
                else t.get("packaging_shrink", "Packaging units (shrink)")
            )
            packaging_used = st.number_input(
                pack_label,
                min_value=0,
                step=1,
                value=st.session_state.prod_packaging,
                help=t.get("packaging_help", "0 = same as production units"),
                key="packaging_used_input"
            )
            st.session_state.prod_packaging = packaging_used
            
            st.markdown("**⏰ " + t.get("shift_info", "Shift") + "**")
            shift_start = st.time_input(
                t.get("shift_start", "Shift start"),
                value=datetime.strptime("08:00", "%H:%M").time(),
                key="shift_start_input"
            )
            shift_end = st.time_input(
                t.get("shift_end", "Shift end"),
                value=datetime.strptime("02:00", "%H:%M").time(),
                key="shift_end_input"
            )
            break_minutes = st.number_input(
                t.get("break_minutes_label", "Break (minutes)"),
                min_value=0,
                max_value=240,
                value=180,
                step=15,
                key="break_minutes_input"
            )

        with col2:
            prod_date = st.date_input(t["date_label"], datetime.now(), key="prod_date_input")
            speed = CONFIG[selected_line]["speed"][product]
            st.info(f"⚡ {t.get('line_speed_label', 'Line speed')}: {speed:,} {t.get('bottles_per_hour', 'bottles/hr')}")

            if target > 0:
                _bom = get_bom_unit_info(product)
                _ppu = max(1, _bom["pieces_per_unit"])
                _good = int(target) * _ppu
                _pfused = int(preforms_used) if int(preforms_used) > 0 else _good
                _waste_b = max(0, _pfused - _good)

                try:
                    _s = shift_start.hour * 60 + shift_start.minute
                    _e = shift_end.hour * 60 + shift_end.minute
                    if _e <= _s:
                        _e += 24 * 60
                    _wmin = max(0, (_e - _s) - int(break_minutes))
                    _whr = _wmin / 60.0
                    _theo = speed * _whr
                    _eff = round((_pfused / _theo * 100), 1) if _theo > 0 else 0.0
                    _eff = min(100.0, _eff)
                    _req_h = _pfused / speed if speed > 0 else 0
                    _dt_h = max(0.0, _whr - _req_h)
                    _dt_m = int(round(_dt_h * 60))
                except Exception:
                    _eff, _dt_m, _wmin, _theo = 0.0, 0, 0, 0

                _pkused = int(packaging_used) if int(packaging_used) > 0 else int(target)
                _pk_waste = max(0, _pkused - int(target))

                st.markdown("---")
                st.markdown(t.get("live_preview", "**📊 Live Preview:**"))
                _c1, _c2 = st.columns(2)
                with _c1:
                    st.metric(t.get("good_bottles", "🍶 Good Bottles"), f"{_good:,}")
                    st.metric(t.get("waste_bottles", "🗑️ Waste Bottles"), f"{_waste_b:,}")
                    st.metric(t.get("expected_downtime", "⏱️ Expected Downtime"), f"{_dt_m} {t.get('minutes_word', 'min')}")
                with _c2:
                    st.metric(t.get("efficiency_label", "📈 Efficiency"), f"{_eff}%")
                    st.metric(t.get("packaging_waste_label", "📦 Packaging Waste"), f"{_pk_waste} {t.get('units_word', 'units')}")
                    st.metric(t.get("operating_time_label", "🕐 Operating Time"), f"{round(_wmin/60,1)} {t.get('hours_word', 'hrs')}")

        submitted = st.form_submit_button("💾 " + t.get("save_report", "Save"), width='stretch')

        if submitted:
            if target <= 0:
                st.error("⚠️ " + t.get("qty_gt_zero", "Quantity must be greater than 0"))
            elif not supervisor:
                st.error("⚠️ " + t.get("enter_supervisor", "Please enter supervisor name"))
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

                # ✅ طباعة للتصحيح
                st.write("🔄 جاري استهلاك المواد...")
                
                # استهلاك المواد
                # استهلاك المواد
                raw_ok, raw_msg = consume_materials_db(
                product, 
                target, 
                selected_line,
                preforms_used=preforms_used,      # ✅ العدد الفعلي للبريفورم
                packaging_used=packaging_used      # ✅ الكمية الفعلية للتغليف
             )
                
                if not raw_ok:
                    st.error(f"❌ {raw_msg}")
                else:
                    try:
                        # 1️⃣ حفظ الإنتاج
                        st.write("💾 جاري حفظ التقرير...")
                        record_id = db_manager.save_production(production_data)
                        st.success(f"✅ تم حفظ التقرير: ID={record_id}")
                        
                        # 2️⃣ إضافة المنتج التام
                        st.write("📦 جاري إضافة المنتج التام...")
                        fg_ok, fg_msg = add_to_finished_goods_db(product, target, selected_line)
                        
                        st.success(f"📦 {fg_msg}" if fg_ok else f"⚠️ {fg_msg}")
                        
                        # 3️⃣ إرسال إشعار Telegram ثم الرسالة النهائية
                        try:
                            from helpers import send_telegram
                            tg_msg = f"✅ تم حفظ تقرير إنتاج - ID:{record_id} | منتج: {product} | خط: {selected_line} | كمية: {target:,}"
                            sent = send_telegram(tg_msg)
                            if sent:
                                st.info("📨 تم إرسال إشعار عبر Telegram")
                            else:
                                st.warning("⚠️ لم يتم إرسال إشعار Telegram (تحقق من الإعدادات)")
                        except Exception as _e:
                            st.warning("⚠️ خطأ أثناء محاولة إرسال إشعار Telegram")

                        # 4️⃣ الرسالة النهائية
                        st.success(f"✅ تم حفظ التقرير بنجاح! ID: {record_id}")
                        # ✅ تحديث cache
                        st.session_state.inventory_version = st.session_state.get('inventory_version', 0) + 1
                        st.cache_data.clear()
                        
                        # ✅ انتظر ثانيتين ثم أعد تحميل الصفحة
                        import time
                        st.info("🔄 تم تحديث المخزون. إعادة تحميل الصفحة...")
                        time.sleep(2)
                        st.rerun()
                        
                    except Exception as e:
                        import traceback
                        error_msg = str(e)
                        error_trace = traceback.format_exc()
                        
                        st.error(f"❌ خطأ عند حفظ التقرير: {error_msg}")
                        st.write(f"📋 التفاصيل:\n```\n{error_trace}\n```")
                        
                        # تسجيل الخطأ
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Production save failed: {error_msg}\n{error_trace}")