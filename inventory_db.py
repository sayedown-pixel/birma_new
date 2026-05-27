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
        
        material = session.query(RawMaterial).filter(
            (RawMaterial.name_ar == material_name) | 
            (RawMaterial.name_en == material_name)
        ).first()
        
        if not material:
            return False, f"❌ المادة '{material_name}' غير موجودة"
        
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
        db_manager.add_info_log(
            'inventory',
            f"Stock {transaction_type}: {material_name} - {quantity} {unit}",
            f"New stock: {material.current_stock}, By: {created_by}"
        )
        return True, f"✅ تم تحديث مخزون '{material_name}': الرصيد الجديد {material.current_stock}"
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    try:
        from database import db_manager
        if hasattr(db_manager, 'add_info_log'):
            db_manager.add_info_log(
                'inventory',
                f"Stock {transaction_type}: {material_name} - {quantity} {material.unit}",
                f"New stock: {material.current_stock}, By: {created_by}, Reference: {reference}"
            )
    except Exception as e:
        print(f"Inventory log error: {e}")
    finally:
        session.close()


def consume_materials_db(product, quantity, line):
    """استهلاك المواد الخام من قاعدة البيانات"""
    from utils import get_materials_required
    
    required, error = get_materials_required(product, quantity)
    if error:
        return False, error
    
    session = db_manager.get_session()
    try:
        from database import RawMaterial, RawMaterialTransaction
        
        for material_name, req_qty in required.items():
            material = session.query(RawMaterial).filter(
                (RawMaterial.name_ar == material_name) | 
                (RawMaterial.name_en == material_name)
            ).first()
            
            if not material:
                return False, f"⚠️ المادة {material_name} غير موجودة في قاعدة البيانات"
            
            if material.current_stock < req_qty:
                return False, f"⚠️ عجز في المادة {material_name}: المطلوب {req_qty}، المتوفر {material.current_stock}"
            
            material.current_stock -= req_qty
            material.last_updated = datetime.now()
            
            transaction = RawMaterialTransaction(
                material_id=material.id,
                transaction_type='consumption',
                quantity=req_qty,
                reference=f"Production: {product}",
                notes=f"الخط: {line}",
                created_by=line,
                created_at=datetime.now()
            )
            session.add(transaction)
        
        session.commit()
        return True, "✅ تم استهلاك المواد بنجاح"
        
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        session.close()


def restore_materials_to_db(product, quantity, line):
    """إعادة المواد الخام إلى المخزون (عند حذف سجل إنتاج)"""
    from utils import get_materials_required
    
    required, error = get_materials_required(product, quantity)
    if error:
        return False, error
    
    session = db_manager.get_session()
    try:
        from database import RawMaterial, RawMaterialTransaction
        
        restored = []
        
        for material_name, req_qty in required.items():
            material = session.query(RawMaterial).filter(
                (RawMaterial.name_ar == material_name) | 
                (RawMaterial.name_en == material_name)
            ).first()
            
            if not material:
                continue
            
            material.current_stock += req_qty
            material.last_updated = datetime.now()
            
            transaction = RawMaterialTransaction(
                material_id=material.id,
                transaction_type='adjustment',
                quantity=req_qty,
                reference=f"Restore from deleted production: {product}",
                notes=f"استعادة بعد حذف سجل إنتاج - الخط: {line}",
                created_by="system",
                created_at=datetime.now()
            )
            session.add(transaction)
            restored.append(f"{material_name}: +{req_qty:,.0f}")
        
        session.commit()
        return True, f"✅ تم إعادة: {', '.join(restored)}"
        
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
        session.close()


# ============================================================================
# Finished Goods Stock Management
# ============================================================================

def update_finished_good_stock_db(product_name, quantity, transaction_type, reference='', customer='', notes='', created_by=''):
    """تحديث مخزون منتج تام (إنتاج/تسليم)"""
    session = db_manager.get_session()
    try:
        from database import FinishedGood, FinishedGoodTransaction
        
        good = session.query(FinishedGood).filter(FinishedGood.name == product_name).first()
        
        if not good:
            return False, f"❌ المنتج '{product_name}' غير موجود"
        
        if transaction_type == 'production':
            good.stock_in += quantity
            good.balance += quantity
        elif transaction_type == 'delivery':
            if good.balance < quantity:
                return False, f"❌ رصيد غير كافٍ للمنتج '{product_name}': المتوفر {good.balance}"
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
        
        return True, f"✅ تم تحديث مخزون '{product_name}': الرصيد الجديد {good.balance}"
    except Exception as e:
        session.rollback()
        return False, f"❌ خطأ: {str(e)}"
    finally:
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
    
    return update_finished_good_stock_db(
        db_name, quantity, 'production',
        reference=f"Production from {line}",
        notes=f"إنتاج {quantity} وحدة من {product_name}",
        created_by=line
    )


def restore_finished_goods_from_production_db(product_name, quantity, line):
    """إرجاع منتج تام من المخزون (عند حذف سجل إنتاج)"""
    name_mapping = {
        "200 ml Carton": "Cartoon 200 ml",
        "200 ml Shrink": "Shrink 200 ml",
        "600 ml Carton": "Cartoon 600 ml",
        "1.5 L Shrink": "1.5 Ltr",
        "330 ml Carton": "Cartoon 330 ml",
        "330 ml Shrink": "Shrink 330 ml",
    }
    db_name = name_mapping.get(product_name, product_name)
    
    return update_finished_good_stock_db(
        db_name, -quantity, 'adjustment',
        reference=f"Restore from deleted production",
        notes=f"استرجاع {quantity} وحدة بعد حذف سجل إنتاج - الخط: {line}",
        created_by="system"
    )


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