# inventory.py - نسخة معدلة بالكامل لاستخدام قاعدة البيانات
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from database import save_raw_receipt_to_db, save_delivery_to_db
from utils import send_telegram
from inventory_db import (
    get_raw_materials_df,
    get_finished_goods_df,
    update_raw_material_stock_db,
    update_finished_good_stock_db,
    get_raw_materials_list_for_display
)

# ============================================================================
# Compatibility functions (تحميل البيانات من قاعدة البيانات)
# ============================================================================

def load_raw_materials():
    """تحميل المواد الخام من قاعدة البيانات"""
    return get_raw_materials_df()

def load_finished_goods():
    """تحميل المنتجات التامة من قاعدة البيانات"""
    return get_finished_goods_df()

def update_raw_materials(df_raw):
    """تحديث المواد الخام (يتم التعامل معه عبر قاعدة البيانات مباشرة)"""
    # البيانات محدثة بالفعل في قاعدة البيانات
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
# Apply monthly rollover for finished goods
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
# FG Product Mapping
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

# ============================================================================
# Finished Goods Functions
# ============================================================================

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
        # تحديث DataFrame للعرض
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
    """Remove quantity from finished goods for delivery - باستخدام قاعدة البيانات"""
    db_name = FG_PRODUCT_MAP.get(product_name, product_name)
    
    success, msg = update_finished_good_stock_db(
        db_name, quantity, 'delivery',
        reference="Delivery",
        notes=f"تسليم {quantity} وحدة",
        created_by=st.session_state.get('user_name', '')
    )
    
    if success and df_fg is not None and not df_fg.empty:
        # تحديث DataFrame للعرض
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
        # تحديث DataFrame للعرض
        idx = df_fg[df_fg["Name"] == db_name].index
        if len(idx) > 0:
            idx = idx[0]
            old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
            df_fg.at[idx, "Balance"] = new_balance
            df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if new_balance > old_balance:
                df_fg.at[idx, "In"] = float(df_fg.at[idx, "In"]) + (new_balance - old_balance)
    
    return df_fg, success, msg

def restore_finished_goods_from_production(product_name, quantity, df_fg):
    """Return finished-goods quantity when a production record is deleted"""
    db_name = FG_PRODUCT_MAP.get(product_name, product_name)
    
    success, msg = update_finished_good_stock_db(
        db_name, -quantity, 'adjustment',
        reference="Restore from deleted production",
        notes=f"استرجاع {quantity} وحدة بعد حذف سجل إنتاج",
        created_by="system"
    )
    
    if success and df_fg is not None and not df_fg.empty:
        # تحديث DataFrame للعرض
        idx = df_fg[df_fg["Name"] == db_name].index
        if len(idx) > 0:
            idx = idx[0]
            old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
            df_fg.at[idx, "Balance"] = max(0, old_balance - quantity)
            df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_fg, success, msg

# ============================================================================
# UI Components - Raw Materials
# ============================================================================

def show_raw_materials(df_raw, t):
    """Display raw materials page - باستخدام قاعدة البيانات"""
    st.header("📦 " + t["raw_materials"])
    
    current_lang = st.session_state.get('lang', 'ar')
    
    if df_raw is None or df_raw.empty:
        st.warning("⚠️ لا توجد بيانات مواد خام في قاعدة البيانات")
        # محاولة إعادة التحميل
        if st.button("🔄 محاولة إعادة تحميل البيانات"):
            st.cache_data.clear()
            st.rerun()
        return
    
    # عرض إحصائيات
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_items = len(df_raw)
        st.metric(t.get("items_count", "📦 عدد الأصناف"), f"{total_items:,}")
    with col2:
        total_stock = df_raw['Current_Stock'].sum() if 'Current_Stock' in df_raw.columns else 0
        st.metric(t.get("total_stock", "📊 إجمالي المخزون"), f"{total_stock:,.0f}")
    with col3:
        if 'Min_Stock' in df_raw.columns:
            low_stock = len(df_raw[df_raw['Current_Stock'] <= df_raw['Min_Stock']])
            st.metric(t.get("low_stock", "⚠️ مواد منخفضة"), f"{low_stock:,}")
    with col4:
        if 'Unit_Cost' in df_raw.columns:
            total_value = (df_raw['Current_Stock'] * df_raw['Unit_Cost']).sum()
            st.metric(t.get("total_value", "💰 القيمة الإجمالية"), f"{total_value:,.0f}")
    
    st.markdown("---")
    st.subheader(f"📋 {t.get('raw_materials_list_title', 'Raw Materials List')}")
    
    # اختيار عمود الاسم حسب اللغة
    if current_lang == 'en' and 'Material_Name_EN' in df_raw.columns:
        name_col = 'Material_Name_EN'
        name_label = "Material"
    else:
        name_col = 'Material_Name_AR'
        name_label = t.get("material", "المادة")
    
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
    
    # تسمية الأعمدة
    column_labels = {}
    if 'Material_ID' in display_df.columns:
        column_labels['Material_ID'] = t.get("item_id", "ID") if current_lang == 'ar' else "ID"
    column_labels[name_col] = name_label
    column_labels['Current_Stock'] = t.get("current_stock", "Current Stock") if current_lang == 'ar' else "Stock"
    if 'Min_Stock' in display_df.columns:
        column_labels['Min_Stock'] = t.get("min_stock", "Min Stock") if current_lang == 'ar' else "Min"
    column_labels['Unit'] = t.get("item_unit", "Unit") if current_lang == 'ar' else "Unit"
    
    display_df = display_df.rename(columns=column_labels)
    st.dataframe(display_df, use_container_width=True, height=400)
    
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
            notes = st.text_area("ملاحظات", key="receipt_notes_input_db")
            
            if st.form_submit_button(t["register_receipt"], use_container_width=True):
                if qty <= 0:
                    st.error("⚠️ الكمية يجب أن تكون أكبر من صفر")
                else:
                    success, msg = update_raw_material_stock_db(
                        material, qty, 'receipt',
                        reference=invoice_no,
                        notes=notes,
                        created_by=st.session_state.get('user_name', '')
                    )
                    if success:
                        st.success(msg)
                        # تسجيل في جدول المشتريات للتوافق
                        save_raw_receipt_to_db({
                            'date': str(receipt_date),
                            'material': material,
                            'quantity': qty,
                            'invoice': invoice_no,
                            'notes': notes,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        try:
                            send_telegram(f"📥 استلام مواد خام: {material} - {qty:,.0f}")
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
            st.info(f"{t.get('current_stock', 'الرصيد الحالي')}: {current_qty:,.0f}")
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
            st.warning("🔒 " + t.get("wrong_password", "كلمة المرور غير صحيحة"))
        else:
            st.warning("🔒 " + t.get("admin_password_required", "يرجى إدخال كلمة مرور المشرف للتعديل"))

# ============================================================================
# UI Components - Finished Goods
# ============================================================================

def show_finished_goods(df_fg, t):
    """Display finished goods page - باستخدام قاعدة البيانات"""
    st.header("🏭 " + t["finished_goods"])
    
    current_lang = st.session_state.get('lang', 'ar')
    
    if df_fg is not None and not df_fg.empty:
        df_fg, rolled = apply_monthly_fg_rollover(df_fg.copy())
        if rolled:
            # تحديث قاعدة البيانات
            for _, row in df_fg.iterrows():
                update_finished_good_stock_db(
                    row['Name'], row['Balance'], 'adjustment',
                    notes=f"ترحيل شهري - {row.get('Month_Key', '')}",
                    created_by="system"
                )
            st.success("✅ " + t.get("month_rollover_done", "Monthly balance carried forward"))
    
    if df_fg is None or df_fg.empty:
        st.warning("⚠️ لا توجد بيانات في مخزن الإنتاج التام")
        return
    
    # عرض إحصائيات
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
    
    # عرض الجدول
    display_cols = ['Name', 'Opening_Balance', 'In', 'Out', 'Balance', 'Unit']
    available_cols = [c for c in display_cols if c in df_fg.columns]
    display_df = df_fg[available_cols].copy()
    
    col_labels = {
        'Name': t.get('col_product', 'Product'),
        'Opening_Balance': t.get('opening_balance', 'Opening Balance'),
        'In': t.get('in', 'In'),
        'Out': t.get('out', 'Out'),
        'Balance': t.get('balance', 'Balance'),
        'Unit': t.get('item_unit', 'Unit'),
    }
    display_df = display_df.rename(columns={k: v for k, v in col_labels.items() if k in display_df.columns})
    st.dataframe(display_df, use_container_width=True)
    
    # قسم التسليم
    st.markdown("---")
    tab_delivery, tab_manual = st.tabs(["🚚 " + t["delivery"], "✏️ " + t["manual_adjust"]])
    
    with tab_delivery:
        with st.form("delivery_form_db"):
            product = st.selectbox(t["product"], df_fg["Name"], key="delivery_product_select_db")
            current_balance = df_fg[df_fg["Name"] == product]['Balance'].values[0]
            
            if current_lang == 'en':
                st.info(f"Current Balance: {current_balance:,.0f}")
            else:
                st.info(f"الرصيد الحالي: {current_balance:,.0f}")
            
            qty = st.number_input(t["quantity_to_deliver"], min_value=0, step=100, max_value=int(current_balance), key="delivery_qty_input_db")
            customer = st.text_input(t["customer"], key="delivery_customer_input_db")
            
            if current_lang == 'en':
                delivery_note = st.text_input("Delivery Note Number", help="Enter delivery note/invoice number", key="delivery_note_input_db")
            else:
                delivery_note = st.text_input("رقم سند التحميل", help="أدخل رقم سند التحميل/الفاتورة", key="delivery_note_input_db")
            
            notes = st.text_area(t["note_label"], key="delivery_notes_input_db")

            if st.form_submit_button(t["register_shipping"], use_container_width=True):
                if qty <= 0:
                    st.error("⚠️ الكمية يجب أن تكون أكبر من صفر")
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
                            send_telegram(f"🚚 تسليم: {product} - {qty:,.0f} وحدة - {customer}")
                        except:
                            pass
                        st.success(msg)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)
    
    with tab_manual:
        edit_pw = st.text_input(t["password"], type="password", key="fg_manual_pw_db")
        if edit_pw in ["admin123", "100"]:
            product = st.selectbox(t["product"], df_fg["Name"], key="manual_product_select_db")
            current = df_fg[df_fg["Name"] == product]["Balance"].values[0]
            new_balance = st.number_input(t["new_stock"], min_value=0, value=int(current), step=1000, key="manual_balance_input_db")
            if st.button(t["update"], key="manual_update_db"):
                new_fg, ok, msg = update_finished_goods_manual_balance(product, new_balance, df_fg)
                if ok:
                    update_finished_goods(new_fg)
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
        elif edit_pw:
            st.warning("🔒 كلمة المرور غير صحيحة")
        else:
            st.warning("🔒 يرجى إدخال كلمة مرور المشرف")