# helpers.py - الدوال المساعدة الخالصة
"""
دوال مساعدة لا تعتمد على قاعدة البيانات
"""

import math
import pandas as pd
from datetime import datetime, timedelta
from constants import BOM, SHRINK_PALLET_CONFIG

def get_bom_unit_info(product):
    """الحصول على معلومات BOM للمنتج"""
    info = {
        "pieces_per_unit": 1,
        "packaging_per_unit": 1.0,
        "packaging_is_weight": False,
        "preform_material": None,
    }
    if product not in BOM:
        return info

    for material, qty in BOM[product].items():
        if "بريفورم" in material:
            info["pieces_per_unit"] = int(qty)
            info["preform_material"] = material
        elif "كرتون" in material:
            info["packaging_per_unit"] = float(qty)
            info["packaging_is_weight"] = False
        elif "شرنك" in material:
            info["packaging_per_unit"] = float(qty)
            info["packaging_is_weight"] = True
    return info

def get_materials_required(product, quantity):
    """حساب المواد المطلوبة لإنتاج كمية معينة"""
    if product not in BOM:
        return None, f"المنتج '{product}' غير موجود في BOM"

    required = {}
    for material, qty in BOM[product].items():
        norm_material = _normalize(material)
        if qty < 1:
            required[norm_material] = math.ceil(quantity * qty)
        else:
            required[norm_material] = qty * quantity

    if "Shrink" in product and product in SHRINK_PALLET_CONFIG:
        cfg = SHRINK_PALLET_CONFIG[product]
        spacers = math.ceil(quantity / cfg["units_per_pallet"]) * cfg["spacers_per_pallet"]
        if spacers > 0:
            required[_normalize("فواصل شرنك")] = spacers

    return required, None

def calculate_production_metrics(product, units, shift_start, shift_end, break_minutes, speed_bottles_per_hour, preforms_used=0, packaging_used=0.0):
    """حساب مقاييس الإنتاج"""
    bom = get_bom_unit_info(product)
    pieces_per_unit = max(1, bom["pieces_per_unit"])
    units = int(units)

    good_bottles = units * pieces_per_unit
    final_preforms = int(preforms_used) if int(preforms_used) > 0 else good_bottles
    waste_bottles = max(0, final_preforms - good_bottles)

    try:
        start_total = shift_start.hour * 60 + shift_start.minute
        end_total = shift_end.hour * 60 + shift_end.minute
        if end_total <= start_total:
            end_total += 24 * 60

        shift_minutes = end_total - start_total
        working_minutes = max(0, shift_minutes - int(break_minutes))
        working_hours = working_minutes / 60.0

        theoretical_bottles = speed_bottles_per_hour * working_hours if working_hours > 0 else 0

        if theoretical_bottles > 0:
            efficiency = min(100.0, round((final_preforms / theoretical_bottles) * 100, 1))
        else:
            efficiency = 0.0

        if speed_bottles_per_hour > 0:
            required_hours = final_preforms / speed_bottles_per_hour
            downtime_hours = max(0.0, working_hours - required_hours)
        else:
            downtime_hours = 0.0

        downtime_minutes = int(round(downtime_hours * 60))

        expected_packaging = units
        if int(packaging_used) > 0:
            final_packaging = int(packaging_used)
            packaging_waste = max(0, final_packaging - expected_packaging)
        else:
            final_packaging = expected_packaging
            packaging_waste = 0

        return {
            "pieces_per_unit": pieces_per_unit,
            "good_bottles": good_bottles,
            "bottles_produced": good_bottles,
            "final_preforms": final_preforms,
            "waste_bottles": waste_bottles,
            "working_minutes": working_minutes,
            "working_hours": round(working_hours, 2),
            "downtime_minutes": downtime_minutes,
            "downtime_hours": round(downtime_hours, 2),
            "theoretical_bottles": int(theoretical_bottles),
            "efficiency": efficiency,
            "packaging_waste": packaging_waste,
            "final_packaging": float(final_packaging),
            "line_speed": int(speed_bottles_per_hour),
            "ideal_run_rate": speed_bottles_per_hour / 60.0,
        }
    except Exception:
        return {
            "pieces_per_unit": pieces_per_unit,
            "good_bottles": good_bottles,
            "bottles_produced": good_bottles,
            "final_preforms": final_preforms,
            "waste_bottles": waste_bottles,
            "working_minutes": 0,
            "working_hours": 0.0,
            "downtime_minutes": 0,
            "downtime_hours": 0.0,
            "theoretical_bottles": 0,
            "efficiency": 0.0,
            "packaging_waste": 0,
            "final_packaging": float(units),
            "line_speed": int(speed_bottles_per_hour),
            "ideal_run_rate": speed_bottles_per_hour / 60.0,
        }

# helpers.py - نسخة باستخدام الترجمة من constants

# helpers.py - نسخة مبسطة من get_shift_info

def get_shift_info():
    """الحصول على معلومات الوردية الحالية - نسخة مبسطة"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    # تحديد وقت البريك الحالي
    is_working = True
    current_break = None
    
    # بريك الفطور: 10:00 - 10:30
    if current_hour == 10 and current_minute < 30:
        is_working = False
        current_break = {"start": "10:00", "end": "10:30", "duration": 0.5}
    
    # بريك الغداء: 13:00 - 14:00
    elif current_hour == 13 or (current_hour == 14 and current_minute == 0):
        is_working = False
        current_break = {"start": "13:00", "end": "14:00", "duration": 1.0}
    
    # بريك العصر: 18:00 - 18:30
    elif current_hour == 18 and current_minute < 30:
        is_working = False
        current_break = {"start": "18:00", "end": "18:30", "duration": 0.5}
    
    # بريك الليل: 23:00 - 00:30
    elif current_hour == 23 or (current_hour == 0 and current_minute < 30):
        is_working = False
        current_break = {"start": "23:00", "end": "00:30", "duration": 1.0}
    
    # الحصول على اللغة
    try:
        import streamlit as st
        current_lang = st.session_state.get('lang', 'ar')
    except:
        current_lang = 'ar'
    
    # نص الوردية
    if current_lang == 'en':
        shift_name = "Single Shift (8:00 AM - 2:00 AM)"
    else:
        shift_name = "الوردية الواحدة (8 صباحاً - 2 صباحاً)"
    
    return {
        "shift_start": now.replace(hour=8, minute=0, second=0, microsecond=0),
        "shift_end": (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0),
        "shift_duration_hours": 18,
        "break_times": [],
        "is_working": is_working,
        "current_break": current_break,
        "total_break_hours": 3,
        "working_hours": 15,
        "shift_name": shift_name
    }

def get_production_record_labels(t):
    """الحصول على تسميات أعمدة سجلات الإنتاج"""
    return {
        "id": t.get("col_id", "ID"),
        "date": t.get("col_date", "Date"),
        "line": t.get("col_line", "Line"),
        "product": t.get("col_product", "Product"),
        "output_units": t.get("col_qty_units", "Qty (units)"),
        "waste_bottles": t.get("col_waste_bottles", "Bottle Waste"),
        "packaging_waste": t.get("col_packaging_waste", "Packaging Waste"),
        "line_speed": t.get("col_line_speed_bottles", "Line speed (bottles/hr)"),
        "preforms_used": t.get("preform_actual", "Preforms used"),
        "efficiency": t.get("col_efficiency", "Efficiency %"),
        "downtime_hours": t.get("col_downtime", "Downtime (hrs)"),
        "operating_hours": t.get("col_operating_time", "Operating (hrs)"),
        "supervisor": t.get("col_supervisor", "Supervisor"),
        "oee": t.get("col_oee", "OEE %"),
    }

def load_language(lang_code='ar'):
    """تحميل الترجمة"""
    from constants import LANG
    return LANG.get(lang_code, LANG['ar'])

def get_machine_map(lang_code='ar'):
    """الحصول على خريطة الماكينات"""
    from constants import MACHINE_LABELS, MACHINE_FILES
    labels = MACHINE_LABELS.get(lang_code, MACHINE_LABELS['ar'])
    return dict(zip(labels, MACHINE_FILES))

def send_telegram(msg):
    """إرسال إشعار تلجرام"""
    try:
        import streamlit as st
        import requests
        import urllib.parse
        token = st.secrets.get("telegram", {}).get("bot_token", "")
        chat_id = st.secrets.get("telegram", {}).get("chat_id", "")
        if token and chat_id:
            requests.get(
                f"https://api.telegram.org/bot{token}/sendMessage"
                f"?chat_id={chat_id}&text={urllib.parse.quote(msg)}&parse_mode=Markdown",
                timeout=5
            )
    except Exception:
        pass
# helpers.py - أضف هذه الدالة

def clean_line_name(line):
    """تنظيف اسم الخط للعرض"""
    if not line:
        return ""
    if "الخط الأول" in line or "line 1" in line.lower():
        return "Line 1"
    elif "الخط الثاني" in line or "line 2" in line.lower():
        return "Line 2"
    return line[:15]    

def create_machine_file(filepath):
    """إنشاء ملف صيانة جديد"""
    if "Compressor" in filepath or "AF_Compressor" in filepath:
        sample_data = pd.DataFrame({
            "Cat": ["Daily checks", "Operation check"],
            "No": [1, 1],
            "Name": ["Fill weekly performance log", "Check emergency stop button"],
            "Photo": ["", ""],
            "Tools": ["Pen", "Manual"],
            "Proc": ["Record data", "Manual test"],
            "Freq": ["Daily", "Daily"],
            "Stat": ["Active"] * 2,
            "Note": ["", ""],
            "Staff": ["", ""],
        })
        sample_data.to_excel(filepath, index=False)
    else:
        sample = pd.DataFrame({
            "Cat": ["Mechanical", "Electrical"],
            "No": [1, 2],
            "Name": ["Check bearings", "Calibrate sensors"],
            "Photo": ["", ""],
            "Tools": ["Wrench", "Calibration device"],
            "Proc": ["Check vibrations", "Calibrate per manual"],
            "Freq": ["Daily", "Weekly"],
            "Stat": ["Active"] * 2,
            "Note": ["", ""],
            "Staff": ["", ""],
        })
        sample.to_excel(filepath, index=False)

def find_image_path(photo_name):
    """البحث عن مسار الصورة"""
    if not photo_name or pd.isna(photo_name) or str(photo_name).strip() == "":
        return None
    import os
    possible = [
        photo_name,
        os.path.join("images", photo_name),
        os.path.join("images", os.path.basename(str(photo_name)))
    ]
    for path in possible:
        if os.path.exists(path):
            return path
    return None

def get_scheduled_tasks(df_tasks):
    """الحصول على المهام المجدولة"""
    if df_tasks is None or df_tasks.empty:
        return pd.DataFrame()

    today = datetime.now()
    day_name = today.strftime('%A')
    is_first_month = (today.day == 1)

    freq_col = next((c for c in ['Freq', 'Frequency'] if c in df_tasks.columns), None)
    if freq_col is None:
        return pd.DataFrame()

    if day_name == 'Friday':
        return pd.DataFrame()

    allowed = ['Daily']
    if day_name == 'Saturday':
        allowed.append('Weekly')
    if is_first_month:
        allowed += ['Monthly', '1000h', 'Yearly']

    df = df_tasks.copy()
    df[freq_col] = df[freq_col].astype(str).replace('4 months', 'Monthly')
    result = df[df[freq_col].isin(allowed)]
    return result.reset_index(drop=True)

# ============================================================================
# Internal helpers
# ============================================================================

def _normalize(name: str) -> str:
    """تطبيع الأسماء"""
    import re
    return re.sub(r'\s+', ' ', str(name).strip())

def _get_material_col(df: pd.DataFrame):
    """الحصول على عمود اسم المادة"""
    for col in ["Material_Name_AR", "Material_Name_EN", "Material_Name", "Name", "المادة", "material"]:
        if col in df.columns:
            return col
    return None

def _get_stock_col(df: pd.DataFrame):
    """الحصول على عمود الكمية"""
    for col in ["Current_Stock", "Stock", "الكمية", "quantity", "in_stock"]:
        if col in df.columns:
            return col
    return None