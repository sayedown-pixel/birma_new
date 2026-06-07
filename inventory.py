# inventory.py - الملف المدمج (inventory.py + inventory_db.py)
# تم الدمج مع الحفاظ على جميع الوظائف

import streamlit as st
import pandas as pd
from datetime import datetime
from database import db_manager, save_raw_receipt_to_db, save_delivery_to_db
from utils import send_telegram
from helpers import normalize_material_name, find_raw_materials


# ============================================================================
# دوال جلب البيانات من قاعدة البيانات (كانت في inventory_db.py)
# ============================================================================

def get_raw_materials_df():
    """الحصول على المواد الخام كـ DataFrame للتوافق مع الكود القديم"""
    materials = db_manager.get_all_raw_materials()
    if not materials:
        return pd.DataFrame()
    
    df = pd.DataFrame(materials)
    rename_map = {
        'material_id': 'Material_ID',
        'name_ar': 'Material_Name_AR',
        'name_en': 'Material_Name_EN',
        'current_stock': 'Current_Stock',
        'min_stock': 'Min_Stock',
        'max_stock': 'Max_Stock',
        'unit': 'Unit',
        'unit_cost': 'Unit_Cost',
        'daily_consumption': 'Daily_Consumption'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if 'Material_Name_AR' in df.columns or 'Material_Name_EN' in df.columns:
        df['norm_name_ar'] = df['Material_Name_AR'].fillna('').apply(normalize_material_name) if 'Material_Name_AR' in df.columns else ''
        df['norm_name_en'] = df['Material_Name_EN'].fillna('').apply(normalize_material_name) if 'Material_Name_EN' in df.columns else ''
        df['norm_key'] = df.apply(lambda row: row['norm_name_ar'] if row['norm_name_ar'] else row['norm_name_en'], axis=1)
        if df['norm_key'].nunique() < len(df):
            agg = {
                'Material_ID': 'first',
                'Material_Name_AR': 'first',
                'Material_Name_EN': 'first',
                'Current_Stock': 'sum',
                'Min_Stock': 'min',
                'Max_Stock': 'max',
                'Unit': 'first',
                'Unit_Cost': 'mean',
                'Daily_Consumption': 'mean',
                'last_updated': 'max'
            }
            available = {k: agg[k] for k in agg if k in df.columns}
            df = df.groupby('norm_key', as_index=False).agg(available)
            df = df.drop(columns=[c for c in ['norm_name_ar', 'norm_name_en', 'norm_key'] if c in df.columns])

    return df


def get_finished_goods_df():
    """الحصول على المنتجات التامة كـ DataFrame"""
    goods = db_manager.get_all_finished_goods()
    if not goods:
        return pd.DataFrame()
    
    df = pd.DataFrame(goods)
    
    # ✅ تأكد من وجود عمود Balance
    if 'balance' not in df.columns:
        print("❌ ERROR: 'balance' column not found in finished goods data!")
        st.error("خطأ: عمود الرصيد غير موجود في بيانات المنتجات التامة")
        return pd.DataFrame()
    
    rename_map = {
        'name': 'Name',
        'opening_balance': 'Opening_Balance',
        'stock_in': 'In',
        'stock_out': 'Out',
        'balance': 'Balance',  # ✅ تأكد من التحويل الصحيح
        'unit': 'Unit',
        'month_key': 'Month_Key'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    # ✅ تحويل Balance إلى رقم
    df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce').fillna(0)
    
    print(f"✅ Finished goods loaded: {len(df)} products")
    print(f"   Balances: {df['Balance'].tolist()}")
    
    return df

def get_raw_materials_list_for_display(lang='ar'):
    """الحصول على قائمة المواد الخام للعرض"""
    materials = db_manager.get_all_raw_materials()
    if not materials:
        return []
    if lang == 'ar':
        return [m['name_ar'] for m in materials]
    else:
        return [m['name_en'] for m in materials]


# ============================================================================
# دوال تحديث المخزون (Raw Materials)
# ============================================================================

def update_raw_material_stock_db(material_name, quantity, transaction_type, reference='', notes='', created_by=''):
    """تحديث مخزون مادة خام (وارد/صرف)"""
    session = db_manager.get_session()
    
    try:
        from database import RawMaterial, RawMaterialTransaction
        
        materials = find_raw_materials(session, material_name)
        if not materials:
            return False, f"❌ Material '{material_name}' not found"
        
        material = materials[0]
        
        if transaction_type == 'receipt':
            material.current_stock += quantity
        elif transaction_type == 'consumption':
            if material.current_stock < quantity:
                return False, f"❌ Insufficient stock for '{material_name}': available {material.current_stock}"
            material.current_stock -= quantity
        elif transaction_type == 'adjustment':
            material.current_stock = quantity
        
        material.last_updated = datetime.now()
        
        transaction = RawMaterialTransaction(
            material_id=material.id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            created_by=created_by,
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        try:
            db_manager.add_info_log(
                'inventory',
                f"Stock {transaction_type}: {material_name} - {quantity} {material.unit}",
                f"New stock: {material.current_stock}, By: {created_by}"
            )
        except Exception:
            pass
        return True, f"✅ Stock updated for '{material_name}': new balance {material.current_stock}"
    except Exception as e:
        session.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        session.close()



# inventory.py - تحديث دالة consume_materials_db (الجزء الخاص بالاستيرادات)

def consume_materials_db(product, quantity, line, preforms_used=0, packaging_used=0):
    """استهلاك المواد الخام من قاعدة البيانات"""
    from helpers import get_materials_required
    from database import db_manager
    from database import RawMaterial, RawMaterialTransaction
    from datetime import datetime
    from constants import SHRINK_ROLL_CONVERSION
    # لا نحتاج لاستيراد قواميس الغراء هنا لأنها مستخدمة فقط في get_materials_required
    
    required, error = get_materials_required(product, quantity, preforms_used, packaging_used)
    if error:
        return False, error
    
    print(f"📦 Consuming materials for {product} x{quantity}")
    
    session = None
    try:
        session = db_manager.get_session()
        
        for material_name, req_qty in required.items():
            print(f"   🔍 Looking for: {material_name} - Qty: {req_qty}")
            
            material = session.query(RawMaterial).filter(
                RawMaterial.name_ar == material_name
            ).first()
            if not material:
                material = session.query(RawMaterial).filter(
                    RawMaterial.name_en == material_name
                ).first()
            
            if not material:
                print(f"      ❌ Material not found: {material_name}")
                session.rollback()
                return False, f"⚠️ Material {material_name} not found"
            
            # ✅ معالجة الشرنك
            is_shrink = "شرنك" in material_name and "فواصل" not in material_name
            is_spacer = "فواصل" in material_name
            
            if is_shrink:
                required_rolls = req_qty
                print(f"      🔄 Shrink: {required_rolls:.2f} rolls required")
                
                if material.current_stock < required_rolls:
                    session.rollback()
                    return False, f"⚠️ Shortage in {material_name}: required {required_rolls:.2f} rolls, available {material.current_stock:.2f} rolls"
                
                material.current_stock -= required_rolls
                print(f"      ✅ Stock updated: {material.current_stock:.2f} rolls")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='consumption',
                    quantity=required_rolls,
                    reference=f"Production: {product}",
                    notes=f"الخط: {line} - الكمية: {quantity} وحدة",
                    created_by=line,
                    created_at=datetime.now()
                )
            
            elif is_spacer:
                if material.current_stock < req_qty:
                    session.rollback()
                    return False, f"⚠️ Shortage in {material_name}: required {req_qty}, available {material.current_stock}"
                
                material.current_stock -= req_qty
                print(f"      ✅ Stock updated: {material.current_stock}")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='consumption',
                    quantity=req_qty,
                    reference=f"Production: {product}",
                    notes=f"الخط: {line} - الكمية: {quantity} وحدة",
                    created_by=line,
                    created_at=datetime.now()
                )
            
            else:
                # المواد العادية (بريفورم، غطاء، ليبل، كرتون، غراء)
                if material.current_stock < req_qty:
                    session.rollback()
                    return False, f"⚠️ Shortage in {material_name}: required {req_qty:.3f} {material.unit}, available {material.current_stock:.3f}"
                
                material.current_stock -= req_qty
                print(f"      ✅ Consumed: {material.name_ar} - New stock: {material.current_stock:.3f}")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='consumption',
                    quantity=req_qty,
                    reference=f"Production: {product}",
                    notes=f"الخط: {line} - الكمية: {quantity} وحدة",
                    created_by=line,
                    created_at=datetime.now()
                )
            
            session.add(transaction)
            material.last_updated = datetime.now()
        
        session.commit()
        print(f"   ✅ Consumption successful!")
        return True, "✅ Materials consumed successfully"
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ Error consuming materials: {str(e)}"
    finally:
        if session:
            session.close()

def restore_materials_to_db(product, quantity, line, preforms_used=0, packaging_used=0):
    """إعادة المواد الخام إلى المخزون (عند حذف سجل إنتاج)"""
    from helpers import get_materials_required
    from database import db_manager
    from database import RawMaterial, RawMaterialTransaction
    from datetime import datetime
    from constants import SHRINK_ROLL_CONVERSION, SHRINK_PALLET_CONFIG
    from constants import LABEL_GLUE_CONSUMPTION_GRAM_PER_BOTTLE, CARTON_GLUE_CONSUMPTION_GRAM_PER_CARTON, UNITS_PER_CARTON
    import math
    
    # ✅ إعادة حساب المواد المستهلكة بنفس طريقة الاستهلاك
    required, error = get_materials_required(product, quantity, preforms_used, packaging_used)
    if error:
        return False, error
    
    print(f"🔄 Restoring materials for {product} x{quantity}")
    print(f"   Materials to restore: {required}")
    
    session = None
    try:
        session = db_manager.get_session()
        restored = []
        
        for material_name, req_qty in required.items():
            print(f"🔍 استرجاع: {material_name} - الكمية: {req_qty}")
            
            material = session.query(RawMaterial).filter(
                RawMaterial.name_ar == material_name
            ).first()
            if not material:
                material = session.query(RawMaterial).filter(
                    RawMaterial.name_en == material_name
                ).first()
            
            if not material:
                print(f"   ❌ لم يتم العثور على المادة: {material_name}")
                continue
            
            # تحديد نوع المادة
            is_shrink = "شرنك" in material_name and "فواصل" not in material_name
            is_spacer = "فواصل" in material_name
            is_label_glue = "غراء الليبل" in material_name
            is_carton_glue = "غراء الكرتون" in material_name
            
            # ✅ معالجة الشرنك
            if is_shrink:
                material.current_stock += req_qty
                print(f"   ✅ {material.name_ar}: +{req_qty:.2f} rolls")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='adjustment',
                    quantity=req_qty,
                    reference=f"Restore from deleted production: {product}",
                    notes=f"استعادة بعد حذف سجل إنتاج - الخط: {line}",
                    created_by="system",
                    created_at=datetime.now()
                )
            
            # ✅ معالجة فواصل الشرنك
            elif is_spacer:
                material.current_stock += req_qty
                print(f"   ✅ {material.name_ar}: +{req_qty} spacers")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='adjustment',
                    quantity=req_qty,
                    reference=f"Restore from deleted production: {product}",
                    notes=f"استعادة بعد حذف سجل إنتاج - الخط: {line}",
                    created_by="system",
                    created_at=datetime.now()
                )
            
            # ✅ معالجة المواد الأخرى (بريفورم، غطاء، ليبل، كرتون، غراء)
            else:
                material.current_stock += req_qty
                print(f"   ✅ {material.name_ar}: +{req_qty:.3f} {material.unit}")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='adjustment',
                    quantity=req_qty,
                    reference=f"Restore from deleted production: {product}",
                    notes=f"استعادة بعد حذف سجل إنتاج - الخط: {line}",
                    created_by="system",
                    created_at=datetime.now()
                )
            
            material.last_updated = datetime.now()
            session.add(transaction)
            restored.append(f"{material_name}: +{req_qty:,.3f}")
        
        session.commit()
        print(f"   ✅ Restored: {', '.join(restored)}")
        return True, f"✅ Restored: {', '.join(restored)}"
        
    except Exception as e:
        print(f"❌ خطأ في restore_materials_to_db: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        if session:
            session.close()

# ============================================================================
# دوال إدارة المنتجات التامة (Finished Goods)
# ============================================================================

def update_finished_good_stock_db(product_name, quantity, transaction_type, reference='', customer='', notes='', created_by=''):
    """تحديث مخزون منتج تام"""
    session = None
    try:
        session = db_manager.get_session()
        from database import FinishedGood, FinishedGoodTransaction
        
        good = session.query(FinishedGood).filter(FinishedGood.name == product_name).first()
        if not good:
            return False, f"❌ Product '{product_name}' not found"
        
        print(f"📦 Updating {product_name}: type={transaction_type}, qty={quantity}, current_balance={good.balance}")
        
        if transaction_type == 'production':
            if quantity < 0:
                good.stock_in += quantity
                good.balance += quantity
            else:
                good.stock_in += quantity
                good.balance += quantity
        elif transaction_type == 'delivery':
            if good.balance < quantity:
                return False, f"❌ Insufficient balance: available {good.balance}"
            good.stock_out += quantity
            good.balance -= quantity
        elif transaction_type == 'adjustment':
            good.balance = quantity
        
        good.last_updated = datetime.now()
        
        transaction = FinishedGoodTransaction(
            finished_good_id=good.id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference=reference,
            customer=customer,
            notes=notes,
            created_by=created_by,
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        print(f"   ✅ New balance: {good.balance}")
        return True, f"✅ Stock updated for '{product_name}': new balance {good.balance}"
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        if session:
            session.close()


def add_to_finished_goods_db(product_name, quantity, line):
    """إضافة منتج تام إلى المخزون (عند تسجيل إنتاج)"""
    name_mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink": "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    db_name = name_mapping.get(product_name, product_name)
    
    print(f"🏭 Adding to finished goods: {product_name} -> {db_name}, Qty: {quantity}")
    
    session = None
    try:
        session = db_manager.get_session()
        from database import FinishedGood, FinishedGoodTransaction
        
        good = session.query(FinishedGood).filter(FinishedGood.name == db_name).first()
        if not good:
            print(f"   ❌ Product not found: {db_name}")
            return False, f"❌ Product '{product_name}' not found"
        
        print(f"   ✅ Found: {good.name} | Current balance: {good.balance}")
        if quantity <= 0:
            return False, "⚠️ Quantity must be greater than zero"
        
        good.stock_in += quantity
        good.balance += quantity
        good.last_updated = datetime.now()
        print(f"   ✅ Updated: stock_in={good.stock_in}, balance={good.balance}")
        
        transaction = FinishedGoodTransaction(
            finished_good_id=good.id,
            transaction_type='production',
            quantity=quantity,
            reference=f"Production from {line}",
            notes=f"إنتاج {quantity} وحدة من {product_name}",
            created_by=line,
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        print(f"   ✅ Success!")
        return True, f"✅ Added {quantity:,.0f} units to {db_name}"
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        if session:
            session.close()


def restore_finished_goods_from_production_db(product_name, quantity, line):
    """إرجاع منتج تام من المخزون (عند حذف سجل إنتاج) - نخصم من المنتج التام"""
    name_mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink": "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    db_name = name_mapping.get(product_name, product_name)
    
    session = None
    try:
        session = db_manager.get_session()
        from database import FinishedGood, FinishedGoodTransaction
        from datetime import datetime
        
        good = session.query(FinishedGood).filter(FinishedGood.name == db_name).first()
        if not good:
            return False, f"❌ Product '{product_name}' not found"
        
        print(f"🔍 استرجاع (خصم) المنتج: {db_name}")
        print(f"   المخزون الحالي: {good.balance}")
        print(f"   الكمية المراد خصمها: {quantity}")
        
        new_balance = good.balance - quantity
        if new_balance < 0:
            print(f"   ⚠️ تحذير: الرصيد سيصبح سالباً ({new_balance})، سيتم تعيينه إلى 0")
            new_balance = 0
        
        good.balance = new_balance
        good.stock_in -= quantity
        good.last_updated = datetime.now()
        
        print(f"   المخزون الجديد: {good.balance}")
        
        transaction = FinishedGoodTransaction(
            finished_good_id=good.id,
            transaction_type='adjustment',
            quantity=-quantity,
            reference=f"Restore from deleted production",
            notes=f"حذف إنتاج {quantity} وحدة - الخط: {line}",
            created_by="system",
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        return True, f"✅ Deducted {quantity} units from {db_name}"
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        if session:
            session.close()


# ============================================================================
# دوال التوافق (Compatibility functions) - كانت في inventory.py
# ============================================================================

def load_raw_materials():
    """تحميل المواد الخام من قاعدة البيانات"""
    return get_raw_materials_df()


def load_finished_goods():
    """تحميل المنتجات التامة من قاعدة البيانات"""
    return get_finished_goods_df()


def update_raw_materials(df_raw):
    """تحديث المواد الخام (يتم التعامل معه عبر قاعدة البيانات مباشرة)"""
    return True


def update_finished_goods(df_fg):
    """تحديث المنتجات التامة"""
    return True


def bump_inventory_cache():
    """تحديث cache المخزون"""
    st.session_state["inventory_version"] = st.session_state.get("inventory_version", 0) + 1


def register_inventory_cache_invalidator(callback):
    """تسجيل دالة لمسح cache"""
    global _inventory_cache_invalidator
    _inventory_cache_invalidator = callback


_inventory_cache_invalidator = None


# ============================================================================
# دوال المنتج التام (Finished Goods) - واجهة قديمة
# ============================================================================

FG_PRODUCT_MAP = {
    "200 ml Carton": "Cartoon 200 ml",
    "200 ml Shrink": "Shrink 200 ml",
    "600 ml Carton": "Cartoon 600 ml",
    "1.5 L Shrink": "1.5 Ltr",
    "330 ml Carton": "Cartoon 330 ml",
    "330 ml Shrink": "Shrink 330 ml",
}


def _fg_row_index(df_fg, product_name):
    fg_name = FG_PRODUCT_MAP.get(product_name, product_name)
    idx = df_fg[df_fg["Name"] == fg_name].index
    if len(idx) == 0:
        idx = df_fg[df_fg["Name"].str.contains(fg_name, case=False, na=False)].index
    return idx, fg_name


def add_to_finished_goods(product_name, quantity, df_fg):
    """Add produced quantity to finished goods - باستخدام قاعدة البيانات"""
    name_mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink": "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    db_name = name_mapping.get(product_name, product_name)
    
    success, msg = update_finished_good_stock_db(
        db_name, quantity, 'production',
        reference=f"Production",
        notes=f"إنتاج {quantity} وحدة",
        created_by=st.session_state.get('user_name', '')
    )
    
    if success and df_fg is not None and not df_fg.empty:
        idx = df_fg[df_fg["Name"] == db_name].index
        if len(idx) > 0:
            idx = idx[0]
            old_in = float(df_fg.at[idx, "In"]) if pd.notna(df_fg.at[idx, "In"]) else 0
            old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
            df_fg.at[idx, "In"] = old_in + quantity
            df_fg.at[idx, "Balance"] = old_balance + quantity
            df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_fg, success, msg


def remove_from_finished_goods_delivery(product_name, quantity, df_fg):
    """Remove quantity from finished goods for delivery"""
    db_name = FG_PRODUCT_MAP.get(product_name, product_name)
    
    success, msg = update_finished_good_stock_db(
        db_name, quantity, 'delivery',
        reference="Delivery",
        notes=f"تسليم {quantity} وحدة",
        created_by=st.session_state.get('user_name', '')
    )
    
    if success and df_fg is not None and not df_fg.empty:
        idx = df_fg[df_fg["Name"] == db_name].index
        if len(idx) > 0:
            idx = idx[0]
            old_out = float(df_fg.at[idx, "Out"]) if pd.notna(df_fg.at[idx, "Out"]) else 0
            old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
            df_fg.at[idx, "Out"] = old_out + quantity
            df_fg.at[idx, "Balance"] = old_balance - quantity
            df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_fg, success, msg


def update_finished_goods_manual_balance(product_name, new_balance, df_fg):
    """Manually update finished goods balance"""
    db_name = FG_PRODUCT_MAP.get(product_name, product_name)
    
    success, msg = update_finished_good_stock_db(
        db_name, new_balance, 'adjustment',
        reference="Manual adjustment",
        notes=f"تعديل يدوي للرصيد إلى {new_balance}",
        created_by=st.session_state.get('user_name', '')
    )
    
    if success and df_fg is not None and not df_fg.empty:
        idx = df_fg[df_fg["Name"] == db_name].index
        if len(idx) > 0:
            idx = idx[0]
            old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
            df_fg.at[idx, "Balance"] = new_balance
            df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if new_balance > old_balance:
                df_fg.at[idx, "In"] = float(df_fg.at[idx, "In"]) + (new_balance - old_balance)
    
    return df_fg, success, msg


# ============================================================================
# ترحيل شهري للمنتجات التامة
# ============================================================================

def apply_monthly_fg_rollover(df_fg):
    """
    On the 1st of each month: carry forward balance as Opening_Balance
    and reset monthly In/Out counters for the new month.
    """
    if df_fg is None or df_fg.empty:
        return df_fg, False

    today = datetime.now()
    if today.day != 1:
        return df_fg, False

    month_key = today.strftime("%Y-%m")
    if "Month_Key" not in df_fg.columns:
        df_fg["Month_Key"] = ""
    if "Opening_Balance" not in df_fg.columns:
        df_fg["Opening_Balance"] = 0.0

    if df_fg["Month_Key"].astype(str).eq(month_key).all():
        return df_fg, False

    for idx in df_fg.index:
        if str(df_fg.at[idx, "Month_Key"]) == month_key:
            continue
        balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0.0
        df_fg.at[idx, "Opening_Balance"] = balance
        df_fg.at[idx, "In"] = 0
        df_fg.at[idx, "Out"] = 0
        df_fg.at[idx, "Balance"] = balance
        df_fg.at[idx, "Month_Key"] = month_key
        df_fg.at[idx, "Last_Updated"] = today.strftime("%Y-%m-%d")

    return df_fg, True


# ============================================================================
# واجهات المستخدم (UI Components)
# ============================================================================

# inventory.py - في دالة show_raw_materials

def show_raw_materials(df_raw, t):
    """Display raw materials page - مع دعم اللغة"""
    st.header("📦 " + t["raw_materials"])
    
    current_lang = st.session_state.get('lang', 'ar')
    
    if df_raw is None or df_raw.empty:
        st.warning(t.get("no_raw_materials_db", "⚠️ No raw materials data in database"))
        if st.button(t.get("retry_load", "🔄 Retry loading")):
            st.cache_data.clear()
            st.rerun()
        return
    
    # عرض إحصائيات
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_items = len(df_raw)
        st.metric(t.get("items_count", "📦 Items Count"), f"{total_items:,}")
    with col2:
        total_stock = df_raw['Current_Stock'].sum() if 'Current_Stock' in df_raw.columns else 0
        st.metric(t.get("total_stock", "📊 Total Stock"), f"{total_stock:,.0f}")
    with col3:
        if 'Min_Stock' in df_raw.columns:
            low_stock = len(df_raw[df_raw['Current_Stock'] <= df_raw['Min_Stock']])
            st.metric(t.get("low_stock", "⚠️ Low Stock"), f"{low_stock:,}")
    with col4:
        if 'Unit_Cost' in df_raw.columns:
            total_value = (df_raw['Current_Stock'] * df_raw['Unit_Cost']).sum()
            st.metric(t.get("total_value", "💰 Total Value"), f"{total_value:,.0f}")
    
    st.markdown("---")
    st.subheader(f"📋 {t.get('raw_materials_list_title', 'Raw Materials List')}")
    
    # اختيار عمود الاسم حسب اللغة
    if current_lang == 'en' and 'Material_Name_EN' in df_raw.columns:
        name_col = 'Material_Name_EN'
        name_label = "Material"
    else:
        name_col = 'Material_Name_AR'
        name_label = t.get("material", "Material")
    
    display_cols = []
    if 'Material_ID' in df_raw.columns:
        display_cols.append('Material_ID')
    display_cols.append(name_col)
    display_cols.append('Current_Stock')
    if 'Min_Stock' in df_raw.columns:
        display_cols.append('Min_Stock')
    display_cols.append('Unit')
    
    available_cols = [c for c in display_cols if c in df_raw.columns]
    display_df = df_raw[available_cols].copy()
    
    column_labels = {}
    if 'Material_ID' in display_df.columns:
        column_labels['Material_ID'] = t.get("item_id", "ID") if current_lang == 'ar' else "ID"
    column_labels[name_col] = name_label
    column_labels['Current_Stock'] = t.get("current_stock", "Current Stock") if current_lang == 'ar' else "Stock"
    if 'Min_Stock' in display_df.columns:
        column_labels['Min_Stock'] = t.get("min_stock", "Min Stock") if current_lang == 'ar' else "Min"
    
    # ✅ ترجمة وحدة القياس
    unit_label = t.get("unit", "Unit")
    column_labels['Unit'] = unit_label
    
    display_df = display_df.rename(columns=column_labels)
    
    if 'Unit' in display_df.columns:
        # ترجمة قيم الوحدة نفسها
        unit_translation = {
            'قطعة': t.get("piece", "piece") if current_lang == 'ar' else "piece",
            'كجم': t.get("kg", "kg") if current_lang == 'ar' else "kg",
            'رول': t.get("roll", "roll") if current_lang == 'ar' else "roll",
        }
        display_df['Unit'] = display_df['Unit'].replace(unit_translation)
    
    st.dataframe(display_df, width='stretch', height=400)
    
    # باقي الكود كما هو...
    
    # قسم استلام مشتريات
    st.markdown("---")
    with st.expander("📥 " + t["receipt"]):
        with st.form("receipt_form_db"):
            col1, col2 = st.columns(2)
            with col1:
                material_options = df_raw[name_col].tolist()
                material = st.selectbox(t["material"], material_options, key="receipt_material_select_db")
                qty = st.number_input(t["quantity"], min_value=0, step=1000, key="receipt_qty_input_db")
            with col2:
                invoice_no = st.text_input(t["invoice"], key="receipt_invoice_input_db")
                receipt_date = st.date_input(t["receipt_date"], key="receipt_date_input_db")
            notes = st.text_area(t.get("note_label", "Notes"), key="receipt_notes_input_db")
            
            if st.form_submit_button(t["register_receipt"], width='stretch'):
                if qty <= 0:
                    st.error(t.get("quantity_greater_than_zero", "⚠️ Quantity must be greater than zero"))
                else:
                    success, msg = update_raw_material_stock_db(
                        material, qty, 'receipt',
                        reference=invoice_no,
                        notes=notes,
                        created_by=st.session_state.get('user_name', '')
                    )
                    if success:
                        st.success(msg)
                        save_raw_receipt_to_db({
                            'date': str(receipt_date),
                            'material': material,
                            'quantity': qty,
                            'invoice': invoice_no,
                            'notes': notes,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        try:
                            send_telegram(f"📥 Raw materials receipt: {material} - {qty:,.0f}")
                        except:
                            pass
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)
    
    # قسم تعديل المخزون اليدوي
    st.markdown("---")
    with st.expander("✏️ " + t["edit_stock"]):
        edit_pw = st.text_input(t["password"], type="password", key="raw_manual_edit_pw_db")
        if edit_pw in ["admin123", "100"]:
            material = st.selectbox(t["material"], df_raw[name_col].tolist(), key="raw_manual_material_db")
            current_row = df_raw[df_raw[name_col] == material].iloc[0]
            current_qty = float(current_row['Current_Stock'])
            st.info(f"{t.get('current_stock', 'Current Stock')}: {current_qty:,.0f}")
            new_qty = st.number_input(t["new_stock"], min_value=0, value=int(current_qty), step=1000, key="raw_manual_new_qty_db")
            
            if st.button(t["update"], key="raw_manual_update_db"):
                success, msg = update_raw_material_stock_db(
                    material, new_qty, 'adjustment',
                    notes="تعديل يدوي للمخزون",
                    created_by=st.session_state.get('user_name', '')
                )
                if success:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
        elif edit_pw:
            st.warning("🔒 " + t.get("wrong_password", "Wrong password"))
        else:
            st.warning("🔒 " + t.get("admin_password_required", "Please enter admin password to edit"))


# inventory.py - في بداية دالة show_finished_goods

def show_finished_goods(df_fg, t):
    """Display finished goods page"""
    
    # ✅ للتحقق - اطبع البيانات الفعلية
    st.write("### Debug: Raw data from database")
    if df_fg is not None and not df_fg.empty:
        # عرض أول 5 صفوف من البيانات
        st.dataframe(df_fg[['Name', 'Balance']].head(10), width='stretch')
        st.caption(f"Total rows: {len(df_fg)}")
    
    # باقي الكود كما هو...
    """Display finished goods page - مع دعم اللغة"""
    st.header("🏭 " + t["finished_goods"])
    
    current_lang = st.session_state.get('lang', 'ar')
    
    if df_fg is not None and not df_fg.empty:
        df_fg, rolled = apply_monthly_fg_rollover(df_fg.copy())
        if rolled:
            for _, row in df_fg.iterrows():
                update_finished_good_stock_db(
                    row['Name'], row['Balance'], 'adjustment',
                    notes=f"ترحيل شهري - {row.get('Month_Key', '')}",
                    created_by="system"
                )
            st.success("✅ " + t.get("month_rollover_done", "Monthly balance carried forward"))
    
    if df_fg is None or df_fg.empty:
        st.warning(t.get("fg_no_data", "⚠️ No finished goods data available"))
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        total_in = df_fg['In'].sum() if 'In' in df_fg.columns else 0
        st.metric("📥 " + t['in'], f"{total_in:,.0f}")
    with col2:
        total_out = df_fg['Out'].sum() if 'Out' in df_fg.columns else 0
        st.metric("📤 " + t['out'], f"{total_out:,.0f}")
    with col3:
        total_balance = df_fg['Balance'].sum() if 'Balance' in df_fg.columns else 0
        st.metric("⚖️ " + t['balance'], f"{total_balance:,.0f}")
    
    st.markdown("---")
    st.subheader(f"📋 {t.get('finished_goods_list_title', 'Finished Goods List')}")
    
    display_cols = ['Name', 'Opening_Balance', 'In', 'Out', 'Balance', 'Unit']
    available_cols = [c for c in display_cols if c in df_fg.columns]
    display_df = df_fg[available_cols].copy()
    
    # ✅ ترجمة وحدة القياس
    unit_label = t.get("unit", "Unit")
    
    # ترجمة قيم الوحدة نفسها
    if 'Unit' in display_df.columns:
        unit_translation = {
            'قطعة': t.get("piece", "piece") if current_lang == 'ar' else "piece",
            'كرتون': t.get("carton", "carton") if current_lang == 'ar' else "carton",
            'شرنك': t.get("shrink", "shrink") if current_lang == 'ar' else "shrink",
            'كجم': t.get("kg", "kg") if current_lang == 'ar' else "kg",
        }
        display_df['Unit'] = display_df['Unit'].replace(unit_translation)
    
    col_labels = {
        'Name': t.get('col_product', 'Product'),
        'Opening_Balance': t.get('opening_balance', 'Opening Balance'),
        'In': t.get('in', 'In'),
        'Out': t.get('out', 'Out'),
        'Balance': t.get('balance', 'Balance'),
        'Unit': unit_label,
    }
    display_df = display_df.rename(columns={k: v for k, v in col_labels.items() if k in display_df.columns})
    st.dataframe(display_df, width='stretch')
    
    st.markdown("---")
    tab_delivery, tab_manual = st.tabs(["🚚 " + t["delivery"], "✏️ " + t["manual_adjust"]])

# inventory.py - داخل tab_delivery (الكود النهائي بدون on_change)

# inventory.py - في دالة show_finished_goods، استبدل tab_delivery بالكامل

    with tab_delivery:
        
        # ✅ اختيار المنتج خارج الفورم (حتى يتغير الرصيد ديناميكياً)
        product = st.selectbox(
            t["product"], 
            df_fg["Name"].tolist(),
            key="delivery_product_select"
        )
        
        # ✅ حساب الرصيد الحالي مباشرة من df_fg
        current_row = df_fg[df_fg["Name"] == product]
        if not current_row.empty:
            current_balance = float(current_row["Balance"].iloc[0])
        else:
            current_balance = 0
        
        # ✅ عرض الرصيد الحالي
        st.info(f"💰 {t.get('current_balance', 'Current Balance')}: {current_balance:,.0f}")
        
        # ✅ الفورم يحتوي فقط على باقي الحقول (بدون selectbox)
        with st.form("delivery_form_db"):
            
            max_delivery = max(0, int(current_balance))
            
            if current_balance <= 0:
                st.error(f"⚠️ {t.get('out_of_stock', 'Out of stock')}! {t.get('cannot_deliver', 'Cannot deliver this product')}")
            
            qty = st.number_input(
                t["quantity_to_deliver"], 
                min_value=0, 
                step=100, 
                max_value=max_delivery, 
                key="delivery_qty_input_db",
                disabled=(current_balance <= 0)
            )
            
            customer = st.text_input(t["customer"], key="delivery_customer_input_db")
            delivery_note = st.text_input(
                t.get("delivery_note_label", "Delivery Note Number"), 
                help=t.get("delivery_note_help", "Enter delivery note/invoice number"), 
                key="delivery_note_input_db"
            )
            notes = st.text_area(t["note_label"], key="delivery_notes_input_db")

            if st.form_submit_button(t["register_shipping"], width='stretch'):
                if qty <= 0:
                    st.error(t.get("quantity_greater_than_zero", "⚠️ Quantity must be greater than zero"))
                elif current_balance <= 0:
                    st.error(t.get("out_of_stock", "⚠️ Out of stock! Cannot deliver"))
                else:
                    new_fg, ok, msg = remove_from_finished_goods_delivery(product, qty, df_fg)
                    if ok:
                        update_finished_goods(new_fg)
                        save_delivery_to_db({
                            'date': str(datetime.now().date()),
                            'product': product,
                            'quantity': qty,
                            'customer': customer,
                            'delivery_note': delivery_note,
                            'notes': notes,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        try:
                            from helpers import send_telegram
                            send_telegram(f"🚚 تحميل منتج تام: {product} - {qty:,.0f} وحدة - العميل: {customer}")
                        except:
                            pass
                        
                        st.success(msg)
                        st.cache_data.clear()
                        st.session_state.inventory_version = st.session_state.get('inventory_version', 0) + 1
                        st.rerun()
                    else:
                        st.error(msg)
    
    with tab_manual:
        edit_pw = st.text_input(t["password"], type="password", key="fg_manual_pw_db")
        if edit_pw in ["admin123", "100"]:
            product = st.selectbox(t["product"], df_fg["Name"], key="manual_product_select_db")
            current = df_fg[df_fg["Name"] == product]["Balance"].values[0]
            default_value = max(0, int(current))
            new_balance = st.number_input(
                t["new_stock"], 
                min_value=0, 
                value=default_value, 
                step=1000, 
                key="manual_balance_input_db"
            )
            if st.button(t["update"], key="manual_update_db"):
                new_fg, ok, msg = update_finished_goods_manual_balance(product, new_balance, df_fg)
                if ok:
                    update_finished_goods(new_fg)
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
        elif edit_pw:
            st.warning("🔒 " + t.get("wrong_password", "Wrong password"))
        else:
            st.warning("🔒 " + t.get("admin_password_required", "Please enter admin password to edit"))