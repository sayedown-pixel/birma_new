# inventory_db.py - نسخة كاملة
import pandas as pd
from database import db_manager
from datetime import datetime

# ============================================================================
# Functions to get data as DataFrame
# ============================================================================

def get_raw_materials_df():
    """الحصول على المواد الخام كـ DataFrame للتوافق مع الكود القديم"""
    materials = db_manager.get_all_raw_materials()
    if not materials:
        return pd.DataFrame()
    
    from helpers import normalize_material_name
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
    rename_map = {
        'name': 'Name',
        'opening_balance': 'Opening_Balance',
        'stock_in': 'In',
        'stock_out': 'Out',
        'balance': 'Balance',
        'unit': 'Unit',
        'month_key': 'Month_Key'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


# ============================================================================
# Raw Materials Stock Management
# ============================================================================

def update_raw_material_stock_db(material_name, quantity, transaction_type, reference='', notes='', created_by=''):
    """تحديث مخزون مادة خام (وارد/صرف)"""
    session = db_manager.get_session()
    
    try:
        from database import RawMaterial, RawMaterialTransaction
        from helpers import find_raw_materials
        
        materials = find_raw_materials(session, material_name)
        if not materials:
            return False, f"❌ المادة '{material_name}' غير موجودة"
        
        material = materials[0]
        
        if transaction_type == 'receipt':
            material.current_stock += quantity
        elif transaction_type == 'consumption':
            if material.current_stock < quantity:
                return False, f"❌ رصيد غير كافٍ للمادة '{material_name}': المتوفر {material.current_stock}"
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
        return True, f"✅ تم تحديث مخزون '{material_name}': الرصيد الجديد {material.current_stock}"
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        session.close()


# inventory_db.py - استبدل دالة consume_materials_db

# inventory_db.py - استبدل دالة consume_materials_db

def consume_materials_db(product, quantity, line, preforms_used=0, packaging_used=0):
    """استهلاك المواد الخام من قاعدة البيانات"""
    from helpers import get_materials_required
    from database import db_manager
    from database import RawMaterial, RawMaterialTransaction
    from datetime import datetime
    from constants import SHRINK_ROLL_CONVERSION
    
    required, error = get_materials_required(product, quantity, preforms_used, packaging_used)
    if error:
        return False, error
    
    print(f"📦 Consuming materials for {product} x{quantity}")
    print(f"   Preforms actual: {preforms_used}, Packaging actual: {packaging_used}")
    print(f"   Required: {required}")
    
    session = None
    try:
        session = db_manager.get_session()
        
        for material_name, req_qty in required.items():
            print(f"   🔍 Looking for: {material_name}")
            
            # البحث عن المادة
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
                return False, f"⚠️ المادة {material_name} غير موجودة"
            
            print(f"      ✅ Found: {material.name_ar} | Stock: {material.current_stock} | Need: {req_qty}")
            
            # ✅ معالجة خاصة للشرنك (جميع الأنواع)
            is_shrink = False
            pieces_per_roll = 1
            
            for shrink_name, roll_pieces in SHRINK_ROLL_CONVERSION.items():
                if shrink_name in material_name:
                    is_shrink = True
                    pieces_per_roll = roll_pieces
                    break
            
            if is_shrink:
                # تحويل المطلوب من قطعة إلى رول
                required_rolls = req_qty / pieces_per_roll
                
                print(f"      🔄 Shrink conversion: {req_qty} pieces = {required_rolls:.2f} rolls")
                print(f"      📦 Pieces per roll: {pieces_per_roll}")
                
                if material.current_stock < required_rolls:
                    print(f"      ❌ Insufficient stock! Need: {required_rolls:.2f} rolls, Available: {material.current_stock} rolls")
                    session.rollback()
                    return False, f"⚠️ عجز في المادة {material_name}: المطلوب {required_rolls:.2f} رول، المتوفر {material.current_stock} رول"
                
                # خصم الرولات
                material.current_stock -= required_rolls
                print(f"      ✅ Stock updated: {material.current_stock:.2f} rolls")
                
                # تسجيل الحركة (نخزن الكمية بالقطع للتقرير، ولكن نضيف ملاحظة بالرول)
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='consumption',
                    quantity=req_qty,
                    reference=f"Production: {product}",
                    notes=f"الخط: {line} - الكمية: {quantity} وحدة - المستهلك: {required_rolls:.2f} رول ({req_qty:,.0f} قطعة)",
                    created_by=line,
                    created_at=datetime.now()
                )
            else:
                # المواد العادية (بريفورم، غطاء، ليبل، كرتون)
                if material.current_stock < req_qty:
                    print(f"      ❌ Insufficient stock!")
                    session.rollback()
                    return False, f"⚠️ عجز في المادة {material_name}: المطلوب {req_qty}، المتوفر {material.current_stock}"
                
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
            
            material.last_updated = datetime.now()
            session.add(transaction)
        
        session.commit()
        print(f"   ✅ Consumption successful!")
        return True, "✅ تم استهلاك المواد بنجاح"
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ خطأ في استهلاك المواد: {str(e)}"
    finally:
        if session:
            session.close()


def restore_materials_to_db(product, quantity, line, preforms_used=0, packaging_used=0):
    """إعادة المواد الخام إلى المخزون (عند حذف سجل إنتاج)"""
    from helpers import get_materials_required
    from database import db_manager
    from database import RawMaterial, RawMaterialTransaction
    from datetime import datetime
    from constants import SHRINK_ROLL_CONVERSION
    
    required, error = get_materials_required(product, quantity, preforms_used, packaging_used)
    if error:
        return False, error
    
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
            
            # ✅ معالجة خاصة للشرنك (جميع الأنواع)
            is_shrink = False
            pieces_per_roll = 1
            
            for shrink_name, roll_pieces in SHRINK_ROLL_CONVERSION.items():
                if shrink_name in material_name:
                    is_shrink = True
                    pieces_per_roll = roll_pieces
                    break
            
            if is_shrink:
                # تحويل الكمية من قطعة إلى رول للإضافة إلى المخزون
                rolls_to_add = req_qty / pieces_per_roll
                material.current_stock += rolls_to_add
                print(f"   ✅ {material.name_ar}: +{rolls_to_add:.2f} rolls ({req_qty:,.0f} pieces)")
                
                transaction = RawMaterialTransaction(
                    material_id=material.id,
                    transaction_type='adjustment',
                    quantity=req_qty,
                    reference=f"Restore from deleted production: {product}",
                    notes=f"استعادة بعد حذف سجل إنتاج - الخط: {line} - {rolls_to_add:.2f} رول ({req_qty:,.0f} قطعة)",
                    created_by="system",
                    created_at=datetime.now()
                )
            else:
                # المواد العادية
                material.current_stock += req_qty
                print(f"   ✅ {material.name_ar}: +{req_qty}")
                
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
            restored.append(f"{material_name}: +{req_qty:,.0f}")
        
        session.commit()
        return True, f"✅ تم إعادة: {', '.join(restored)}"
        
    except Exception as e:
        print(f"❌ خطأ في restore_materials_to_db: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        if session:
            session.close()
# ============================================================================
# Finished Goods Stock Management
# ============================================================================

# inventory_db.py - استبدل دالة update_finished_good_stock_db

def update_finished_good_stock_db(product_name, quantity, transaction_type, reference='', customer='', notes='', created_by=''):
    """تحديث مخزون منتج تام"""
    from database import db_manager
    from database import FinishedGood, FinishedGoodTransaction
    from datetime import datetime
    
    session = None
    try:
        session = db_manager.get_session()
        good = session.query(FinishedGood).filter(FinishedGood.name == product_name).first()
        
        if not good:
            return False, f"❌ المنتج '{product_name}' غير موجود"
        
        print(f"📦 Updating {product_name}: type={transaction_type}, qty={quantity}, current_balance={good.balance}")
        
        if transaction_type == 'production':
            if quantity < 0:
                # استرجاع (حذف إنتاج): خصم من المنتج التام حتى لو أصبح الرصيد سالبًا
                good.stock_in += quantity
                good.balance += quantity
            else:
                # إضافة إنتاج
                good.stock_in += quantity
                good.balance += quantity
                
        elif transaction_type == 'delivery':
            if good.balance < quantity:
                return False, f"❌ رصيد غير كافٍ: المتوفر {good.balance}"
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
        return True, f"✅ تم تحديث مخزون '{product_name}': الرصيد الجديد {good.balance}"
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        if session:
            session.close()

def add_to_finished_goods_db(product_name, quantity, line):
    """إضافة منتج تام إلى المخزون"""
    from database import db_manager
    from database import FinishedGood, FinishedGoodTransaction
    from datetime import datetime
    
    # تحويل اسم المنتج
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
        
        good = session.query(FinishedGood).filter(FinishedGood.name == db_name).first()
        
        if not good:
            print(f"   ❌ Product not found: {db_name}")
            return False, f"❌ المنتج '{product_name}' غير موجود"
        
        print(f"   ✅ Found: {good.name} | Current balance: {good.balance}")
        
        # ✅ تأكد من أن الكمية موجبة
        if quantity <= 0:
            return False, "⚠️ الكمية يجب أن تكون أكبر من صفر"
        
        # تحديث المخزون
        good.stock_in += quantity
        good.balance += quantity
        good.last_updated = datetime.now()
        print(f"   ✅ Updated: stock_in={good.stock_in}, balance={good.balance}")
        
        # تسجيل الحركة
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
        return True, f"✅ تم إضافة {quantity:,.0f} وحدة إلى مخزن {db_name}"
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ خطأ: {str(e)}"
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
            return False, f"❌ المنتج '{product_name}' غير موجود"
        
        print(f"🔍 استرجاع (خصم) المنتج: {db_name}")
        print(f"   المخزون الحالي: {good.balance}")
        print(f"   الكمية المراد خصمها: {quantity}")
        
        # ✅ تصحيح: نخصم الكمية (ننقص من المنتج التام)
        new_balance = good.balance - quantity
        
        # ✅ إذا كان الرصيد سيصبح سالباً، نضعه صفر
        if new_balance < 0:
            print(f"   ⚠️ تحذير: الرصيد سيصبح سالباً ({new_balance})، سيتم تعيينه إلى 0")
            new_balance = 0
        
        good.balance = new_balance
        good.stock_in -= quantity  # نخصم من الوارد
        good.last_updated = datetime.now()
        
        print(f"   المخزون الجديد: {good.balance}")
        
        transaction = FinishedGoodTransaction(
            finished_good_id=good.id,
            transaction_type='adjustment',
            quantity=-quantity,  # كمية سالبة للتسجيل
            reference=f"Restore from deleted production",
            notes=f"حذف إنتاج {quantity} وحدة - الخط: {line}",
            created_by="system",
            created_at=datetime.now()
        )
        session.add(transaction)
        session.commit()
        
        return True, f"✅ تم خصم {quantity} وحدة من {db_name}"
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        if session:
            session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        if session:
            session.close()

def consume_materials_from_db(product, quantity, line):
    """استهلاك المواد الخام من قاعدة البيانات (اسم بديل)"""
    return consume_materials_db(product, quantity, line)


def get_raw_materials_list_for_display(lang='ar'):
    """الحصول على قائمة المواد الخام للعرض"""
    materials = db_manager.get_all_raw_materials()
    if not materials:
        return []
    
    if lang == 'ar':
        return [m['name_ar'] for m in materials]
    else:
        return [m['name_en'] for m in materials]