# utils.py - النسخة الكاملة مع استيراد pandas

import pandas as pd
from constants import USERS, ROLE_PERMISSIONS, CONFIG, BOM, LANG
from helpers import (
    get_bom_unit_info,
    get_materials_required,
    calculate_production_metrics,
    get_shift_info,
    load_language,
    get_machine_map,
    send_telegram,
    create_machine_file,
    find_image_path,
    get_scheduled_tasks,
    get_production_record_labels,
    _normalize,
    _get_material_col,
    _get_stock_col
)

# ============================================================================
# دوال تعتمد على قاعدة البيانات
# ============================================================================

def get_auto_reorder_suggestions(df_raw, df_main):
    """الحصول على اقتراحات إعادة الطلب - مع دعم اللغة"""
    suggestions = []
    if df_raw is None or df_raw.empty:
        return suggestions

    # الحصول على اللغة الحالية
    try:
        import streamlit as st
        current_lang = st.session_state.get('lang', 'ar')
    except:
        current_lang = 'ar'

    # تحديد عمود الاسم المناسب حسب اللغة
    if current_lang == 'en' and 'Material_Name_EN' in df_raw.columns:
        material_col = 'Material_Name_EN'
    elif 'Material_Name_AR' in df_raw.columns:
        material_col = 'Material_Name_AR'
    else:
        material_col = _get_material_col(df_raw)
    
    stock_col = _get_stock_col(df_raw)
    
    if not material_col or not stock_col:
        return suggestions

    for _, row in df_raw.iterrows():
        current = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
        min_stock = float(row.get('Min_Stock', 0)) if pd.notna(row.get('Min_Stock', 0)) else 0

        if current <= min_stock and min_stock > 0:
            suggested_qty = max(0, int(min_stock * 2 - current))
            urgency = "high" if current < min_stock / 2 else "medium"
            suggestions.append({
                "material": str(row[material_col]),  # ✅ الآن يستخدم الاسم حسب اللغة
                "current": int(current),
                "min_stock": int(min_stock),
                "suggested_qty": suggested_qty,
                "urgency": urgency
            })

    return suggestions


def get_stock_prediction_calculated(df_raw, df_main, selected_line):
    """توقع نفاذ المخزون - مع دعم اللغة"""
    predictions = []
    if df_raw is None or df_raw.empty:
        return predictions

    # الحصول على اللغة الحالية
    try:
        import streamlit as st
        current_lang = st.session_state.get('lang', 'ar')
    except:
        current_lang = 'ar'

    # تحديد عمود الاسم المناسب حسب اللغة
    if current_lang == 'en' and 'Material_Name_EN' in df_raw.columns:
        material_col = 'Material_Name_EN'
    elif 'Material_Name_AR' in df_raw.columns:
        material_col = 'Material_Name_AR'
    else:
        material_col = _get_material_col(df_raw)
    
    stock_col = _get_stock_col(df_raw)
    
    if not material_col or not stock_col:
        return predictions

    DAILY_CONSUMPTION = {
        "غطاء": 1000000, "caps blue": 1000000,
        "بريفورم 200 مل": 600000, "preform 200": 600000,
        "بريفورم 330 مل": 600000, "preform 330": 600000,
        "بريفورم 600 مل": 300000, "preform 600": 300000,
        "بريفورم 1.5 لتر": 150000, "preform 1.5": 150000,
        "ليبل 200 مل": 600000, "label 200": 600000,
        "ليبل 330 مل": 600000, "label 330": 600000,
        "ليبل 600 مل": 300000, "label 600": 300000,
        "ليبل 1.5 لتر": 150000, "label 1.5": 150000,
        "كرتون 200 مل": 12500, "raw cartoon 200": 12500,
        "كرتون 330 مل": 15000, "raw cartoon 330": 15000,
        "كرتون 600 مل": 10000, "raw cartoon 600": 10000,
        "شرنك 200 مل": 15, "shrink 200": 15,
        "شرنك 330 مل": 15, "shrink 330": 15,
        "شرنك 1.5 لتر": 12, "shrink 1.5": 12,
        "فواصل شرنك": 5000, "shrink spacers": 5000,
        "غراء الليبل": 5, "adhesive": 5,
        "غراء الكرتون": 20, "hotmelt": 20,
    }

    for _, row in df_raw.iterrows():
        # الحصول على الاسم حسب اللغة للعرض
        mat_name_display = str(row[material_col]) if pd.notna(row[material_col]) else ""
        
        # الحصول على الأسماء للبحث (عربي وإنجليزي)
        mat_name_ar = str(row.get('Material_Name_AR', '')) if 'Material_Name_AR' in df_raw.columns else ""
        mat_name_en = str(row.get('Material_Name_EN', '')) if 'Material_Name_EN' in df_raw.columns else ""
        
        current_stock = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
        
        daily_consumption = 0
        for key, value in DAILY_CONSUMPTION.items():
            if key in mat_name_ar or key in mat_name_en or mat_name_ar in key or mat_name_en in key:
                daily_consumption = value
                break
        
        if daily_consumption > 0 and current_stock > 0:
            days_left = current_stock / daily_consumption
            if days_left < 60:
                status = "critical" if days_left <= 3 else "warning" if days_left <= 7 else "info"
                predictions.append({
                    "material": mat_name_display,  # ✅ الآن يستخدم الاسم حسب اللغة
                    "current": int(current_stock),
                    "days_left": round(days_left, 1),
                    "daily_consumption": daily_consumption,
                    "status": status
                })
        elif current_stock <= 0:
            predictions.append({
                "material": mat_name_display,
                "current": 0,
                "days_left": 0,
                "daily_consumption": daily_consumption,
                "status": "critical"
            })

    predictions.sort(key=lambda x: x["days_left"])
    return predictions


def get_marquee_recommendations(df_raw, df_main, df_fg, t, lang, selected_line):
    """الحصول على توصيات الشريط المتحرك"""
    recommendations = []
    en = lang == "en"

    reorder = get_auto_reorder_suggestions(df_raw, df_main)
    for rec in reorder[:3]:
        if rec["urgency"] == "high":
            recommendations.append(
                f"🔴 {t.get('auto_reorder', '')}: {rec['material']} - "
                f"{t.get('marquee_stock', 'Stock' if en else 'الرصيد')} {rec['current']:,}"
            )
        else:
            recommendations.append(
                f"🟡 {t.get('auto_reorder', '')}: {rec['material']} - "
                f"{t.get('marquee_suggested', 'Suggested' if en else 'الكمية المقترحة')} {rec['suggested_qty']:,}"
            )

    stock_pred = get_stock_prediction_calculated(df_raw, df_main, selected_line)
    for pred in stock_pred[:3]:
        if pred["status"] == "critical":
            recommendations.append(
                f"⚠️ {t.get('stock_prediction', '')}: {pred['material']} "
                f"{t.get('marquee_deplete_in', 'runs out in' if en else 'سينفذ خلال')} {pred['days_left']} "
                f"{t.get('marquee_days', 'days' if en else 'يوم')}"
            )

    if df_fg is not None and not df_fg.empty and "Balance" in df_fg.columns:
        fg_balance = df_fg["Balance"].sum()
        if fg_balance <= 0:
            recommendations.append(f"🏭 {t.get('fg_balance', '')}: {t.get('marquee_fg_empty', 'empty - increase production' if en else 'فارغ - يرجى زيادة الإنتاج')}")

    if not recommendations:
        recommendations.append(f"✅ {t.get('all_good', 'All good' if en else 'جميع المواد آمنة')} ✅")

    return recommendations


def delete_production_record(record_id, df_raw, df_fg):
    """حذف سجل إنتاج وإرجاع المواد"""
    from database import db_manager
    from inventory_db import restore_materials_to_db, restore_finished_goods_from_production_db

    record = db_manager.get_production_by_id(int(record_id))
    if not record:
        return False, "السجل غير موجود"

    product = record["product"]
    quantity = int(record["output_units"])
    line = record.get("line", "")

    raw_ok, raw_msg = restore_materials_to_db(product, quantity, line)
    if not raw_ok:
        return False, raw_msg

    fg_ok, fg_msg = restore_finished_goods_from_production_db(product, quantity, line)
    if not fg_ok:
        return False, fg_msg

    if not db_manager.delete_production(int(record_id)):
        return False, "فشل حذف السجل من قاعدة البيانات"

    msg = raw_msg
    if fg_msg:
        msg += f" | {fg_msg}"
    return True, msg


def calculate_days_until_depletion(df_raw, df_main, selected_line):
    """حساب عدد الأيام حتى نفاذ المواد - مع دعم اللغة"""
    if df_raw is None or df_raw.empty:
        return df_raw
    
    # الحصول على اللغة الحالية
    try:
        import streamlit as st
        current_lang = st.session_state.get('lang', 'ar')
    except:
        current_lang = 'ar'

    # تحديد عمود الاسم المناسب حسب اللغة للعرض
    if current_lang == 'en' and 'Material_Name_EN' in df_raw.columns:
        display_material_col = 'Material_Name_EN'
    elif 'Material_Name_AR' in df_raw.columns:
        display_material_col = 'Material_Name_AR'
    else:
        display_material_col = _get_material_col(df_raw)
    
    stock_col = _get_stock_col(df_raw)
    
    if not display_material_col or not stock_col:
        if df_raw is not None:
            df_raw['Days_Until_Depletion'] = 999.0
        return df_raw
    
    DAILY_CONSUMPTION = {
        "غطاء": 1000000, "caps blue": 1000000,
        "بريفورم 200 مل": 600000, "preform 200": 600000,
        "بريفورم 330 مل": 600000, "preform 330": 600000,
        "بريفورم 600 مل": 300000, "preform 600": 300000,
        "بريفورم 1.5 لتر": 150000, "preform 1.5": 150000,
        "ليبل 200 مل": 600000, "label 200": 600000,
        "ليبل 330 مل": 600000, "label 330": 600000,
        "ليبل 600 مل": 300000, "label 600": 300000,
        "ليبل 1.5 لتر": 150000, "label 1.5": 150000,
        "كرتون 200 مل": 12500, "raw cartoon 200": 12500,
        "كرتون 330 مل": 15000, "raw cartoon 330": 15000,
        "كرتون 600 مل": 10000, "raw cartoon 600": 10000,
        "شرنك 200 مل": 15, "shrink 200": 15,
        "شرنك 330 مل": 15, "shrink 330": 15,
        "شرنك 1.5 لتر": 12, "shrink 1.5": 12,
        "فواصل شرنك": 5000, "shrink spacers": 5000,
        "غراء الليبل": 5, "adhesive": 5,
        "غراء الكرتون": 20, "hotmelt": 20,
    }
    
    df_result = df_raw.copy()
    depletion_days = []
    material_names = []
    
    for idx, row in df_result.iterrows():
        # الاسم للعرض حسب اللغة
        mat_name_display = str(row[display_material_col]) if pd.notna(row[display_material_col]) else ""
        
        # الأسماء للبحث
        mat_name_ar = str(row.get('Material_Name_AR', '')) if 'Material_Name_AR' in df_raw.columns else ""
        mat_name_en = str(row.get('Material_Name_EN', '')) if 'Material_Name_EN' in df_raw.columns else ""
        
        try:
            current_stock = float(row[stock_col]) if pd.notna(row[stock_col]) else 0.0
        except (ValueError, TypeError):
            current_stock = 0.0
        
        daily_usage = 0.0
        for key, value in DAILY_CONSUMPTION.items():
            if key in mat_name_ar or key in mat_name_en or mat_name_ar in key or mat_name_en in key:
                daily_usage = value
                break
        
        if daily_usage > 0 and current_stock > 0:
            days = current_stock / daily_usage
            depletion_days.append(round(days, 1))
        elif current_stock <= 0:
            depletion_days.append(0.0)
        else:
            depletion_days.append(999.0)
        
        material_names.append(mat_name_display)
    
    if 'Material_Display_Name' not in df_result.columns:
        df_result['Material_Display_Name'] = material_names
    df_result['Days_Until_Depletion'] = depletion_days
    
    return df_result


# إعادة تصدير كل شيء للتوافق مع الكود القديم
__all__ = [
    'USERS', 'ROLE_PERMISSIONS', 'CONFIG', 'BOM', 'LANG',
    'get_bom_unit_info', 'get_materials_required', 'calculate_production_metrics',
    'get_shift_info', 'load_language', 'get_machine_map', 'send_telegram',
    'create_machine_file', 'find_image_path', 'get_scheduled_tasks',
    'get_production_record_labels', 'get_auto_reorder_suggestions',
    'get_stock_prediction_calculated', 'get_marquee_recommendations',
    'delete_production_record', 'calculate_days_until_depletion'
]