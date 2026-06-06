# utils.py - النسخة الكاملة مع استيراد pandas
# utils.py - أضف هذا الاستيراد في بداية الملف مع بقية الاستيرادات

from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
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
# utils.py - أضف هذه الدالة في بداية الملف بعد الاستيرادات

def debug_downtime_data(df_maintenance, df_production, start_date, end_date, selected_line):
    """دالة مساعدة لتصحيح أخطاء تحليل التوقف"""
    print("=" * 50)
    print("DEBUG: Downtime Analysis Data Check")
    print("=" * 50)
    
    if df_maintenance is not None:
        print(f"Maintenance DF shape: {df_maintenance.shape}")
        if 'date' in df_maintenance.columns:
            print(f"Maintenance date range: {df_maintenance['date'].min()} to {df_maintenance['date'].max()}")
        print(f"Maintenance columns: {df_maintenance.columns.tolist()}")
    else:
        print("Maintenance DF is None")
    
    if df_production is not None:
        print(f"Production DF shape: {df_production.shape}")
        if 'date' in df_production.columns:
            print(f"Production date range: {df_production['date'].min()} to {df_production['date'].max()}")
        print(f"Production columns: {df_production.columns.tolist()}")
    else:
        print("Production DF is None")
    
    print(f"Filter dates: {start_date} to {end_date}")
    print(f"Selected line: {selected_line}")
    print("=" * 50)
# ============================================================================
# دوال تعتمد على قاعدة البيانات
# ============================================================================

# utils.py - استبدل دالة get_auto_reorder_suggestions بهذه النسخة

def get_auto_reorder_suggestions(df_raw, df_main):
    """الحصول على اقتراحات إعادة الطلب - تعرض جميع المواد المنخفضة"""
    suggestions = []
    if df_raw is None or df_raw.empty:
        print("❌ get_auto_reorder_suggestions: df_raw is None or empty")
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
        material_col = None
        for col in ['Material_Name_AR', 'Material_Name_EN', 'Material_Name', 'Name', 'المادة']:
            if col in df_raw.columns:
                material_col = col
                break
    
    stock_col = None
    for col in ['Current_Stock', 'Stock', 'in_stock', 'الكمية']:
        if col in df_raw.columns:
            stock_col = col
            break
    
    if not material_col or not stock_col:
        return suggestions

    # ✅ جمع جميع المواد التي وصلت للحد الأدنى أو أقل
    for _, row in df_raw.iterrows():
        current = float(row[stock_col]) if pd.notna(row[stock_col]) else 0
        min_stock = float(row.get('Min_Stock', 0)) if pd.notna(row.get('Min_Stock', 0)) else 0
        material_name = str(row[material_col]) if pd.notna(row[material_col]) else ""
        
        # ✅ تشمل جميع المواد التي وصلت للحد الأدنى أو أقل
        if min_stock > 0 and current <= min_stock:
            suggested_qty = max(0, int(min_stock * 2 - current))
            
            # تحديد مستوى الخطورة
            if current <= 0:
                urgency = "critical"
                level = "🔴 Out of Stock"
            elif current <= min_stock / 2:
                urgency = "critical"
                level = "🔴 Critical"
            elif current <= min_stock:
                urgency = "warning"
                level = "🟡 Warning"
            else:
                urgency = "info"
                level = "🔵 Info"
            
            suggestions.append({
                "material": material_name,
                "current": int(current),
                "min_stock": int(min_stock),
                "suggested_qty": suggested_qty,
                "urgency": urgency,
                "level": level,
                "percentage": round((current / min_stock * 100), 1) if min_stock > 0 else 0
            })
        
        # ✅ أيضاً تشمل المواد التي نفدت بالكامل (حتى لو لم يكن لها حد أدنى)
        elif current <= 0:
            suggested_qty = int(min_stock * 2) if min_stock > 0 else 1000
            suggestions.append({
                "material": material_name,
                "current": 0,
                "min_stock": int(min_stock) if min_stock > 0 else 0,
                "suggested_qty": suggested_qty,
                "urgency": "critical",
                "level": "🔴 Out of Stock",
                "percentage": 0
            })

    # ترتيب حسب الأكثر خطورة أولاً
    suggestions.sort(key=lambda x: (
        0 if x['urgency'] == 'critical' else 1 if x['urgency'] == 'warning' else 2,
        x['percentage']
    ))
    
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


# utils.py - في دالة delete_production_record

def delete_production_record(record_id, df_raw, df_fg):
    from database import db_manager
    from inventory import restore_materials_to_db, restore_finished_goods_from_production_db

    record = db_manager.get_production_by_id(int(record_id))
    if not record:
        return False, "Record not found"

    product = record["product"]
    quantity = int(record["output_units"])
    line = record.get("line", "")
    
    # ✅ الحصول على القيم الفعلية من السجل
    preforms_used = record.get("preforms_used", 0)
    packaging_used = record.get("packaging_used", 0)

    # ✅ تمرير القيم الفعلية
    raw_ok, raw_msg = restore_materials_to_db(product, quantity, line, preforms_used, packaging_used)
    if not raw_ok:
        return False, raw_msg

    fg_ok, fg_msg = restore_finished_goods_from_production_db(product, quantity, line)
    if not fg_ok:
        return False, fg_msg

    if not db_manager.delete_production(int(record_id)):
        return False, "Failed to delete record from database"

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
# utils.py - أضف هذه الدوال في نهاية الملف

import numpy as np
from sklearn.linear_model import LinearRegression
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
# utils.py - استبدل دالة get_enhanced_downtime_analysis بالكامل

# utils.py - استبدل دالة get_enhanced_downtime_analysis بالكامل

# utils.py - استبدل دالة get_enhanced_downtime_analysis بالكامل

def get_enhanced_downtime_analysis(df_maintenance, df_production, start_date, end_date, selected_line=None):
    """
    تحليل متقدم لوقت التوقف يجمع بيانات من الصيانة والإنتاج
    """
    # تحميل الترجمة الحالية
    try:
        import streamlit as st
        current_lang = st.session_state.get('lang', 'ar')
        from constants import LANG
        t = LANG.get(current_lang, LANG['ar'])
    except:
        # قاموس افتراضي للترجمة
        t = {
            'downtime_category_mechanical': 'Mechanical',
            'downtime_category_electrical': 'Electrical', 
            'downtime_category_operational': 'Operational',
            'downtime_category_raw_materials': 'Raw Materials',
            'downtime_category_other': 'Other',
            'downtime_category_critical_breakdown': 'Critical Breakdown',
            'downtime_category_performance_loss': 'Performance Loss',
            'downtime_category_minor_stop': 'Minor Stop',
            'downtime_category_uncategorized': 'Uncategorized',
            'trend_increasing': 'Increasing',
            'trend_decreasing': 'Decreasing',
            'trend_stable': 'Stable',
            'rec_good_performance': 'Good performance! Continue monitoring',
            'rec_action_maintain_current': 'Maintain current maintenance system',
            'rec_impact_stability': 'Production stability',
        }
    
    # قائمة لتجميع جميع أحداث التوقف
    downtime_events = []
    
    # التأكد من أن start_date و end_date من نوع datetime
    if isinstance(start_date, date):
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, date):
        end_date = datetime.combine(end_date, datetime.max.time())
    
    # ==================== 1. معالجة بيانات الصيانة ====================
    if df_maintenance is not None and not df_maintenance.empty:
        maint_df = df_maintenance.copy()
        
        # تحويل التاريخ إذا لزم الأمر
        if 'date' in maint_df.columns:
            if not pd.api.types.is_datetime64_any_dtype(maint_df['date']):
                maint_df['date'] = pd.to_datetime(maint_df['date'])
            
            # فلترة حسب التاريخ
            mask = (maint_df['date'] >= start_date) & (maint_df['date'] <= end_date)
            maint_df = maint_df[mask]
        
        # فلترة حسب الخط
        if selected_line and 'line' in maint_df.columns:
            maint_df = maint_df[maint_df['line'] == selected_line]
        
        # معالجة سجلات الأعطال فقط
        if 'type' in maint_df.columns:
            breakdowns = maint_df[maint_df['type'] == 'breakdown']
        else:
            breakdowns = maint_df
        
        for _, row in breakdowns.iterrows():
            # تحديد الفئة مع الترجمة
            category_en = row.get('downtime_category', 'uncategorized')
            if pd.isna(category_en) or category_en == '':
                category_en = 'uncategorized'
            
            # تعيين الفئة المترجمة
            category_map = {
                'Mechanical': t.get('downtime_category_mechanical', 'Mechanical'),
                'Electrical': t.get('downtime_category_electrical', 'Electrical'),
                'Operational': t.get('downtime_category_operational', 'Operational'),
                'Raw Materials': t.get('downtime_category_raw_materials', 'Raw Materials'),
                'Other': t.get('downtime_category_other', 'Other'),
                'Critical_Breakdown': t.get('downtime_category_critical_breakdown', 'Critical Breakdown'),
                'Performance_Loss': t.get('downtime_category_performance_loss', 'Performance Loss'),
                'Minor_Stop': t.get('downtime_category_minor_stop', 'Minor Stop'),
            }
            category_display = category_map.get(category_en, t.get('downtime_category_uncategorized', 'Uncategorized'))
            
            # الحصول على مدة التوقف
            duration = 0
            if 'downtime_minutes' in row:
                duration = float(row['downtime_minutes']) if pd.notna(row['downtime_minutes']) else 0
            elif 'duration_minutes' in row:
                duration = float(row['duration_minutes']) if pd.notna(row['duration_minutes']) else 0
            
            if duration > 0:
                downtime_events.append({
                    'date': row['date'],
                    'source': 'maintenance',
                    'machine': row.get('machine', 'Unknown'),
                    'category': category_en,
                    'category_display': category_display,
                    'duration_minutes': duration,
                    'description': row.get('issue', '')[:100] if 'issue' in row else '',
                    'technician': row.get('technician', ''),
                    'spare_parts': row.get('spare_parts', '')
                })
    
    # ==================== 2. معالجة بيانات الإنتاج ====================
    if df_production is not None and not df_production.empty:
        prod_df = df_production.copy()
        
        # تحويل التاريخ إذا لزم الأمر
        if 'date' in prod_df.columns:
            if not pd.api.types.is_datetime64_any_dtype(prod_df['date']):
                prod_df['date'] = pd.to_datetime(prod_df['date'])
            
            # فلترة حسب التاريخ
            mask = (prod_df['date'] >= start_date) & (prod_df['date'] <= end_date)
            prod_df = prod_df[mask]
        
        # فلترة حسب الخط
        if selected_line and 'line' in prod_df.columns:
            prod_df = prod_df[prod_df['line'] == selected_line]
        
        # تصفية الإنتاج فقط
        if 'type' in prod_df.columns:
            prod_df = prod_df[prod_df['type'] == 'Production']
        
        for _, row in prod_df.iterrows():
            downtime = 0
            if 'downtime_minutes' in row:
                downtime = float(row['downtime_minutes']) if pd.notna(row['downtime_minutes']) else 0
            
            if downtime > 0:
                efficiency = 100
                if 'efficiency' in row:
                    efficiency = float(row['efficiency']) if pd.notna(row['efficiency']) else 100
                
                if efficiency < 50:
                    category_en = 'Critical_Breakdown'
                    category_display = t.get('downtime_category_critical_breakdown', 'Critical Breakdown')
                elif efficiency < 75:
                    category_en = 'Performance_Loss'
                    category_display = t.get('downtime_category_performance_loss', 'Performance Loss')
                else:
                    category_en = 'Minor_Stop'
                    category_display = t.get('downtime_category_minor_stop', 'Minor Stop')
                
                downtime_events.append({
                    'date': row['date'],
                    'source': 'production',
                    'machine': row.get('line', selected_line or 'Unknown'),
                    'category': category_en,
                    'category_display': category_display,
                    'duration_minutes': downtime,
                    'description': f"Production: {row.get('product', '')} - Efficiency {efficiency:.1f}%" if 'product' in row else '',
                    'technician': row.get('supervisor', ''),
                    'spare_parts': ''
                })
    
    if not downtime_events:
        return None
    
    # تحويل إلى DataFrame
    df_events = pd.DataFrame(downtime_events)
    df_events = df_events.sort_values('date')
    
    # ==================== 3. حساب الإحصائيات الأساسية ====================
    stats = {
        'total_events': len(df_events),
        'total_downtime_minutes': df_events['duration_minutes'].sum(),
        'total_downtime_hours': df_events['duration_minutes'].sum() / 60,
        'avg_downtime_per_event': df_events['duration_minutes'].mean(),
        'max_downtime_event': df_events['duration_minutes'].max(),
        'min_downtime_event': df_events['duration_minutes'].min(),
        'std_downtime': df_events['duration_minutes'].std()
    }
    
    # ==================== 4. تحليل Pareto ====================
    category_analysis = df_events.groupby(['category', 'category_display']).agg({
        'duration_minutes': ['sum', 'count', 'mean']
    }).round(1)
    category_analysis.columns = ['total_minutes', 'event_count', 'avg_minutes']
    category_analysis = category_analysis.sort_values('total_minutes', ascending=False)
    
    if stats['total_downtime_minutes'] > 0:
        category_analysis['cumulative_percentage'] = (category_analysis['total_minutes'].cumsum() / stats['total_downtime_minutes']) * 100
        category_analysis['pareto_class'] = category_analysis['cumulative_percentage'].apply(
            lambda x: 'A (80%)' if x <= 80 else ('B (95%)' if x <= 95 else 'C (100%)')
        )
    
    # ==================== 5. تحليل الماكينات ====================
    machine_analysis = df_events.groupby('machine').agg({
        'duration_minutes': ['sum', 'count', 'mean']
    }).round(1)
    machine_analysis.columns = ['total_minutes', 'event_count', 'avg_minutes']
    machine_analysis = machine_analysis.sort_values('total_minutes', ascending=False)
    
    # ==================== 6. تحليل الاتجاه الزمني ====================
    daily_downtime = df_events.groupby(df_events['date'].dt.date)['duration_minutes'].sum().reset_index()
    daily_downtime.columns = ['date', 'total_minutes']
    
    daily_counts = df_events.groupby(df_events['date'].dt.date)['duration_minutes'].count().reset_index()
    daily_counts.columns = ['date', 'event_count']
    
    daily_trend = pd.merge(daily_downtime, daily_counts, on='date', how='outer')
    daily_trend['event_count'] = daily_trend['event_count'].fillna(0).astype(int)
    daily_trend = daily_trend.sort_values('date')
    
    # توقع الاتجاه
    trend_forecast = {'direction': t.get('trend_stable', 'Stable'), 'forecast_7days_avg': daily_trend['total_minutes'].mean() if not daily_trend.empty else 0}
    
    if len(daily_trend) >= 3:
        try:
            x = np.arange(len(daily_trend))
            y = daily_trend['total_minutes'].values
            
            if len(np.unique(y)) > 1:
                slope = np.polyfit(x, y, 1)[0]
                if slope > 1:
                    trend_forecast['direction'] = t.get('trend_increasing', 'Increasing')
                elif slope < -1:
                    trend_forecast['direction'] = t.get('trend_decreasing', 'Decreasing')
                else:
                    trend_forecast['direction'] = t.get('trend_stable', 'Stable')
                trend_forecast['slope'] = round(slope, 2)
        except Exception as e:
            pass
    
    # ==================== 7. توصيات ذكية ====================
    recommendations = []
    
    if not category_analysis.empty:
        top_category = category_analysis.iloc[0]
        top_category_name = top_category.name[1] if isinstance(top_category.name, tuple) else str(top_category.name)
        
        if stats['total_downtime_minutes'] > 0:
            top_category_percent = (top_category['total_minutes'] / stats['total_downtime_minutes']) * 100
            
            if top_category_percent > 30:
                suggestions = {
                    'ar': f"⚠️ فئة '{top_category_name}' تسبب {top_category_percent:.1f}% من إجمالي وقت التوقف",
                    'en': f"⚠️ Category '{top_category_name}' causes {top_category_percent:.1f}% of total downtime"
                }
                actions = {
                    'ar': f"تحليل أسباب {top_category_name} ووضع خطة عمل مستهدفة",
                    'en': f"Analyze '{top_category_name}' causes and create targeted action plan"
                }
                impacts = {
                    'ar': f'متوقع تقليل التوقف بنسبة {min(50, top_category_percent):.0f}%',
                    'en': f'Expected downtime reduction of {min(50, top_category_percent):.0f}%'
                }
                
                recommendations.append({
                    'priority': 'high',
                    'area': top_category_name,
                    'suggestion': suggestions.get(current_lang if 'current_lang' in dir() else 'ar', suggestions['ar']),
                    'action': actions.get(current_lang if 'current_lang' in dir() else 'ar', actions['ar']),
                    'impact': impacts.get(current_lang if 'current_lang' in dir() else 'ar', impacts['ar'])
                })
    
    if not recommendations:
        good_perf = {
            'ar': '✅ أداء جيد! استمر في المراقبة',
            'en': '✅ Good performance! Continue monitoring'
        }
        maintain_action = {
            'ar': 'الحفاظ على نظام الصيانة الحالي',
            'en': 'Maintain current maintenance system'
        }
        stability_impact = {
            'ar': 'استقرار الإنتاج',
            'en': 'Production stability'
        }
        lang_code = current_lang if 'current_lang' in dir() else 'ar'
        
        recommendations.append({
            'priority': 'low',
            'area': 'General',
            'suggestion': good_perf.get(lang_code, good_perf['ar']),
            'action': maintain_action.get(lang_code, maintain_action['ar']),
            'impact': stability_impact.get(lang_code, stability_impact['ar'])
        })
    
    return {
        'events': df_events,
        'stats': stats,
        'category_analysis': category_analysis,
        'machine_analysis': machine_analysis,
        'daily_trend': daily_trend,
        'trend_forecast': trend_forecast,
        'recommendations': recommendations
    }