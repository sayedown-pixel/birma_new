# helpers.py - نسخة كاملة مع الدوال الجديدة

import math
import pandas as pd
from datetime import datetime, timedelta
from constants import BOM, SHRINK_PALLET_CONFIG

# ============================================================================
# Line Name Normalization
# ============================================================================
def normalize_line_name(line):
    """تحويل اسم الخط إلى الصيغة الإنجليزية"""
    if not line:
        return ""
    if "الخط الأول" in str(line) or "line 1" in str(line).lower():
        return "Line 1"
    elif "الخط الثاني" in str(line) or "line 2" in str(line).lower():
        return "Line 2"
    return str(line)

def clean_line_name(line):
    """تنظيف اسم الخط للعرض (اسم بديل)"""
    return normalize_line_name(line)


# ============================================================================
# BOM Helper Functions
# ============================================================================

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
# helpers.py - أضف هذه الدوال

def get_shrink_roll_quantity(material_name, required_pieces):
    """
    تحويل الكمية المطلوبة من القطع إلى عدد الرولات
    material_name: اسم المادة (شرنك 200 مل / شرنك 330 مل / شرنك 1.5 لتر)
    required_pieces: عدد القطع المطلوبة
    """
    from constants import SHRINK_ROLL_CONVERSION
    
    # البحث عن اسم المادة في قاموس التحويل
    for key, pieces_per_roll in SHRINK_ROLL_CONVERSION.items():
        if key in material_name:
            # حساب عدد الرولات المطلوبة (تقريب لأعلى)
            rolls_needed = math.ceil(required_pieces / pieces_per_roll)
            actual_pieces = rolls_needed * pieces_per_roll
            print(f"   📦 {material_name}: مطلوب {required_pieces} قطعة → {rolls_needed} رول ({actual_pieces} قطعة)")
            return actual_pieces, pieces_per_roll
    
    # إذا لم يكن شرنك، أرجع نفس الكمية
    return required_pieces, 1

def normalize_material_name(name):
    """Normalize raw material names to avoid duplicates from extra spaces or case."""
    if not isinstance(name, str):
        return ""
    cleaned = name.replace("\u00A0", " ").strip()
    cleaned = " ".join(cleaned.split())
    return cleaned.lower()


def find_raw_materials(session, material_name):
    """Find all raw material records matching a normalized material name."""
    from database import RawMaterial

    if not material_name:
        return []

    normalized = normalize_material_name(material_name)
    if not normalized:
        return []

    exact_matches = session.query(RawMaterial).filter(
        (RawMaterial.name_ar == material_name) |
        (RawMaterial.name_en == material_name)
    ).all()
    if exact_matches:
        return exact_matches

    materials = session.query(RawMaterial).filter(RawMaterial.is_active == True).all()
    matches = []
    for material in materials:
        if normalize_material_name(material.name_ar) == normalized or normalize_material_name(material.name_en) == normalized:
            matches.append(material)
    return matches




# helpers.py - استبدل دالة get_materials_required بالكامل

# helpers.py - استبدل الجزء الخاص بغراء الليبل

# helpers.py - استبدل دالة get_materials_required بالكامل

# helpers.py - استبدل الجزء الخاص بفحص الكرتون وغراء الكرتون

def get_materials_required(product, quantity, preforms_used=0, packaging_used=0):
    """
    حساب المواد المطلوبة لإنتاج كمية معينة
    """
    import math
    from constants import (
        BOM, SHRINK_ROLL_CONVERSION, SHRINK_PALLET_CONFIG,
        LABEL_GLUE_CONSUMPTION_GRAM_PER_BOTTLE,
        CARTON_GLUE_CONSUMPTION_GRAM_PER_CARTON,
        UNITS_PER_CARTON
    )
    
    print(f"🔍 Getting materials for: {product} x{quantity}")
    print(f"   Preforms used (actual): {preforms_used}")
    print(f"   Packaging used (actual): {packaging_used}")
    
    if product not in BOM:
        print(f"   ❌ Product {product} not in BOM")
        return None, f"المنتج '{product}' غير موجود في BOM"

    # ✅ الحصول على عدد القطع (العبوات) لكل وحدة
    from helpers import get_bom_unit_info
    bom_info = get_bom_unit_info(product)
    pieces_per_unit = bom_info.get("pieces_per_unit", 1)
    
    # ✅ العدد الفعلي للعبوات المنتجة
    actual_bottles = quantity * pieces_per_unit
    print(f"   📊 Actual bottles produced: {actual_bottles:,} (quantity: {quantity:,} × {pieces_per_unit} pcs/unit)")

    required = {}
    
    # ✅ تحديد إذا كان المنتج يحتوي على كرتون (باللغة العربية أو الإنجليزية)
    has_carton = False
    for material in BOM[product].keys():
        if "كرتون" in material or "carton" in material.lower():
            has_carton = True
            break
    
    # ✅ تحديد إذا كان المنتج يحتوي على شرنك
    has_shrink = False
    for material in BOM[product].keys():
        if "شرنك" in material or "shrink" in material.lower():
            has_shrink = True
            break
    
    print(f"   📦 Product contains carton: {has_carton}, contains shrink: {has_shrink}")
    
    for material, qty in BOM[product].items():
        # ==================== البريفورم ====================
        if "بريفورم" in material:
            if preforms_used > 0:
                req_qty = preforms_used
                print(f"   📦 {material}: using actual preforms used = {req_qty:,}")
            else:
                req_qty = qty * quantity
                print(f"   📦 {material}: {qty} x {quantity:,} = {req_qty:,}")

        # ==================== الكرتون ====================
        elif "كرتون" in material or "carton" in material.lower():
            if packaging_used > 0:
                req_qty = packaging_used
                print(f"   📦 {material}: using actual packaging used = {req_qty:,}")
            else:
                req_qty = qty * quantity
                print(f"   📦 {material}: {qty} x {quantity:,} = {req_qty:,}")

        # ==================== الشرنك ====================
        elif "شرنك" in material or "shrink" in material.lower():
            if "فواصل" not in material:
                if packaging_used > 0:
                    rolls_needed = qty * packaging_used
                    print(f"   📦 {material}: {qty} rolls/unit × {packaging_used:,} units = {rolls_needed} rolls required")
                else:
                    rolls_needed = qty * quantity
                    print(f"   📦 {material}: {qty} rolls/unit × {quantity:,} units = {rolls_needed} rolls required")
                
                pieces_per_roll = SHRINK_ROLL_CONVERSION.get(material, 1980)
                req_qty_pieces = rolls_needed * pieces_per_roll
                print(f"   📦 {material}: {rolls_needed} rolls × {pieces_per_roll} pieces/roll = {req_qty_pieces:,.0f} pieces")
                req_qty = rolls_needed
                print(f"   📦 {material}: REQUIRED ROLLS = {req_qty} rolls")
            else:
                # فواصل شرنك
                if packaging_used > 0:
                    actual_units = packaging_used
                else:
                    actual_units = quantity
                
                product_config = SHRINK_PALLET_CONFIG.get(product, {})
                units_per_pallet = product_config.get("units_per_pallet", 1)
                spacers_per_pallet = product_config.get("spacers_per_pallet", 0)
                
                pallets_needed = math.ceil(actual_units / units_per_pallet) if units_per_pallet > 0 else 0
                req_qty = pallets_needed * spacers_per_pallet
                print(f"   📦 {material}: {actual_units:,} units → {pallets_needed} pallets × {spacers_per_pallet} spacers = {req_qty}")

        # ==================== باقي المواد ====================
        else:
            if isinstance(qty, (int, float)):
                if qty < 1:
                    req_qty = quantity * qty
                else:
                    req_qty = qty * quantity
            else:
                req_qty = quantity
            print(f"   📦 {material}: {qty} x {quantity:,} = {req_qty:,}")

        required[material] = req_qty

    # ✅ ✅ ✅ غراء الليبل - يستخدم مع جميع المنتجات
    glue_gram_per_bottle = LABEL_GLUE_CONSUMPTION_GRAM_PER_BOTTLE.get(product, 0.135)
    label_glue_kg = (actual_bottles * glue_gram_per_bottle) / 1000
    required["غراء الليبل"] = label_glue_kg
    print(f"   📦 غراء الليبل: {actual_bottles:,} bottles × {glue_gram_per_bottle}g = {actual_bottles * glue_gram_per_bottle:,.0f}g ({label_glue_kg:.3f} kg)")

    # ✅ ✅ ✅ غراء الكرتون - يستخدم فقط مع المنتجات التي تحتوي على كرتون
    if has_carton:
        if product in CARTON_GLUE_CONSUMPTION_GRAM_PER_CARTON:
            units_per_carton = UNITS_PER_CARTON.get(product, 48)
            cartons_needed = math.ceil(actual_bottles / units_per_carton)
            glue_gram_per_carton = CARTON_GLUE_CONSUMPTION_GRAM_PER_CARTON[product]
            carton_glue_kg = (cartons_needed * glue_gram_per_carton) / 1000
            required["غراء الكرتون"] = carton_glue_kg
            print(f"   📦 غراء الكرتون: {cartons_needed:,} cartons × {glue_gram_per_carton}g = {cartons_needed * glue_gram_per_carton:,.0f}g ({carton_glue_kg:.3f} kg)")
        else:
            print(f"   ⚠️ ملاحظة: المنتج {product} يحتوي على كرتون ولكن لا توجد نسبة استهلاك محددة لغراء الكرتون")
    else:
        print(f"   ℹ️ المنتج {product} لا يحتوي على كرتون (لا يحتاج غراء كرتون)")

    print(f"   ✅ Total materials: {len(required)}")
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


def get_shift_info():
    """الحصول على معلومات الوردية الحالية - نسخة مبسطة"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    is_working = True
    current_break = None
    
    if current_hour == 10 and current_minute < 30:
        is_working = False
        current_break = {"start": "10:00", "end": "10:30", "duration": 0.5}
    elif current_hour == 13 or (current_hour == 14 and current_minute == 0):
        is_working = False
        current_break = {"start": "13:00", "end": "14:00", "duration": 1.0}
    elif current_hour == 18 and current_minute < 30:
        is_working = False
        current_break = {"start": "18:00", "end": "18:30", "duration": 0.5}
    elif current_hour == 23 or (current_hour == 0 and current_minute < 30):
        is_working = False
        current_break = {"start": "23:00", "end": "00:30", "duration": 1.0}
    
    try:
        import streamlit as st
        current_lang = st.session_state.get('lang', 'ar')
    except:
        current_lang = 'ar'
    
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


# helpers.py - استبدل دالة send_telegram بهذه النسخة

def send_telegram(msg):
    """إرسال إشعار تلجرام"""
    try:
        import streamlit as st
        import requests
        import logging
        
        # ✅ استخدام التوكن الذي أعطيته مباشرة (للتجربة)
        token = "8606698058:AAHPTrzp8xCdXkx956aP5W-uH0Z_4daC0Ks"
        chat_id = "7911811172"
        
        # محاولة الحصول من secrets أولاً (إذا كان موجوداً)
        try:
            if hasattr(st, 'secrets'):
                telegram_config = st.secrets.get("telegram", {})
                if telegram_config.get("bot_token"):
                    token = telegram_config.get("bot_token")
                if telegram_config.get("chat_id"):
                    chat_id = telegram_config.get("chat_id")
        except:
            pass
        
        if not token or not chat_id:
            print("⚠️ Telegram: Missing token or chat_id")
            return False
        
        # إرسال الرسالة
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram sent: {msg[:50]}...")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram exception: {e}")
        return False


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