import streamlit as st
import pandas as pd
import os
from datetime import datetime
from database import save_raw_receipt_to_db, save_delivery_to_db
from utils import send_telegram

# استخدام المسار المطلق للملفات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_MATERIALS_FILE = os.path.join(BASE_DIR, "raw.xlsx")
FINISHED_GOODS_FILE = os.path.join(BASE_DIR, "finished_goods.xlsx")


_inventory_cache_invalidator = None


def register_inventory_cache_invalidator(callback):
    """Registered from app.py to clear inventory cache without importing app."""
    global _inventory_cache_invalidator
    _inventory_cache_invalidator = callback


def bump_inventory_cache():
    """Mark inventory stale so the next run reloads Excel (fast, no full app import)."""
    st.session_state["inventory_version"] = st.session_state.get("inventory_version", 0) + 1
    if _inventory_cache_invalidator:
        _inventory_cache_invalidator()


def load_raw_materials():
    """Load raw materials from Excel - بدون رسائل Sidebar مزعجة"""
    
    if not os.path.exists(RAW_MATERIALS_FILE):
        # لا نعرض رسالة Sidebar، فقط نرجع None
        return None
    
    try:
        df_raw = pd.read_excel(RAW_MATERIALS_FILE)
        
        if df_raw.empty:
            return None
        
        # تحويل الأعمدة الرقمية
        numeric_columns = ['Current_Stock', 'Min_Stock', 'Max_Stock', 'Unit_Cost']
        for col in numeric_columns:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
        
        # ملء القيم الفارغة
        text_columns = ['Material_Name_AR', 'Material_Name_EN', 'Unit']
        for col in text_columns:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].fillna('').astype(str)
        
        return df_raw
        
    except Exception as e:
        return None
        
    except Exception as e:
        st.error(f"❌ خطأ في تحميل المواد الخام: {str(e)}")
        return None

def update_raw_materials(df_raw):
    """Update raw materials Excel file"""
    try:
        if df_raw is not None:
            df_raw.to_excel(RAW_MATERIALS_FILE, index=False)
            bump_inventory_cache()
            return True
        return False
    except Exception as e:
        st.error(f"خطأ في حفظ المواد الخام: {e}")
        return False

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


def load_finished_goods():
    """Load finished goods from Excel - بدون رسائل Sidebar مزعجة"""
    
    # إذا كان الملف غير موجود، قم بإنشائه
    if not os.path.exists(FINISHED_GOODS_FILE):
        return create_sample_finished_goods()
    
    try:
        df_fg = pd.read_excel(FINISHED_GOODS_FILE)
        
        if df_fg.empty:
            return create_sample_finished_goods()
        
        if "Opening_Balance" not in df_fg.columns:
            df_fg["Opening_Balance"] = df_fg["Balance"] if "Balance" in df_fg.columns else 0
        if "Month_Key" not in df_fg.columns:
            df_fg["Month_Key"] = ""

        # تحويل الأعمدة الرقمية
        for col in ["In", "Out", "Balance", "Opening_Balance"]:
            if col in df_fg.columns:
                df_fg[col] = pd.to_numeric(df_fg[col], errors='coerce').fillna(0)
        
        df_fg, rolled = apply_monthly_fg_rollover(df_fg)
        if rolled:
            df_fg.to_excel(FINISHED_GOODS_FILE, index=False)
            bump_inventory_cache()
        
        return df_fg
        
    except Exception as e:
        return create_sample_finished_goods()

def update_finished_goods(df_fg):
    """Update finished goods Excel file"""
    try:
        if df_fg is not None:
            df_fg.to_excel(FINISHED_GOODS_FILE, index=False)
            bump_inventory_cache()
            return True
        return False
    except Exception as e:
        st.error(f"خطأ في حفظ المنتج التام: {e}")
        return False

def create_sample_finished_goods():
    """Create sample finished goods file"""
    sample_df = pd.DataFrame({
        'Name': ['Cartoon 200 ml', 'Shrink 200 ml', 'Cartoon 330 ml', 'Shrink 330 ml', 
                 'Cartoon 600 ml', '1.5 Ltr'],
        'Opening_Balance': [0, 0, 0, 0, 0, 0],
        'In': [0, 0, 0, 0, 0, 0],
        'Out': [0, 0, 0, 0, 0, 0],
        'Balance': [0, 0, 0, 0, 0, 0],
        'Unit': ['قطعة', 'قطعة', 'قطعة', 'قطعة', 'قطعة', 'قطعة'],
        'Month_Key': [''] * 6,
        'Last_Updated': [datetime.now().strftime("%Y-%m-%d")] * 6
    })
    sample_df.to_excel(FINISHED_GOODS_FILE, index=False)
    st.success(f"✅ تم إنشاء ملف {FINISHED_GOODS_FILE}")
    return sample_df

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


def restore_finished_goods_from_production(product_name, quantity, df_fg):
    """Return finished-goods quantity when a production record is deleted."""
    if df_fg is None or df_fg.empty:
        return df_fg, False, "⚠️ لا توجد بيانات منتج تام"

    idx, fg_name = _fg_row_index(df_fg, product_name)
    if len(idx) == 0:
        return df_fg, False, f"⚠️ المنتج {product_name} غير موجود في مخزن التام"

    idx = idx[0]
    qty = int(quantity)
    old_in = float(df_fg.at[idx, "In"]) if pd.notna(df_fg.at[idx, "In"]) else 0
    old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0

    df_fg.at[idx, "In"] = max(0, old_in - qty)
    df_fg.at[idx, "Balance"] = max(0, old_balance - qty)
    df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df_fg, True, f"✅ تم إرجاع {qty:,.0f} من {fg_name} إلى المخزن"


def add_to_finished_goods(product_name, quantity, df_fg):
    """Add produced quantity to finished goods"""
    idx, fg_name = _fg_row_index(df_fg, product_name)
    if len(idx) == 0:
        return df_fg, False, f"⚠️ المنتج {product_name} غير موجود في المخزن"
    
    idx = idx[0]
    old_in = float(df_fg.at[idx, "In"]) if pd.notna(df_fg.at[idx, "In"]) else 0
    old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
    
    df_fg.at[idx, "In"] = old_in + quantity
    df_fg.at[idx, "Balance"] = old_balance + quantity
    df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_fg, True, f"✅ تم إضافة {quantity:,.0f} وحدة إلى المخزن"

def remove_from_finished_goods_delivery(product_name, quantity, df_fg):
    """Remove quantity from finished goods for delivery"""
    idx = df_fg[df_fg["Name"] == product_name].index
    if len(idx) == 0:
        idx = df_fg[df_fg["Name"].str.contains(product_name, case=False, na=False)].index
    
    if len(idx) == 0:
        return df_fg, False, f"⚠️ المنتج {product_name} غير موجود"
    
    idx = idx[0]
    current_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
    
    if current_balance < quantity:
        return df_fg, False, f"⚠️ الرصيد غير كاف! المتوفر: {current_balance:,.0f}"
    
    old_out = float(df_fg.at[idx, "Out"]) if pd.notna(df_fg.at[idx, "Out"]) else 0
    
    df_fg.at[idx, "Out"] = old_out + quantity
    df_fg.at[idx, "Balance"] = current_balance - quantity
    df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_fg, True, f"✅ تم تسليم {quantity:,.0f} وحدة"

def update_finished_goods_manual_balance(product_name, new_balance, df_fg):
    """Manually update finished goods balance"""
    idx = df_fg[df_fg["Name"] == product_name].index
    if len(idx) == 0:
        idx = df_fg[df_fg["Name"].str.contains(product_name, case=False, na=False)].index
    
    if len(idx) == 0:
        return df_fg, False, f"⚠️ المنتج {product_name} غير موجود"
    
    idx = idx[0]
    old_balance = float(df_fg.at[idx, "Balance"]) if pd.notna(df_fg.at[idx, "Balance"]) else 0
    old_in = float(df_fg.at[idx, "In"]) if pd.notna(df_fg.at[idx, "In"]) else 0
    
    diff = new_balance - old_balance
    
    df_fg.at[idx, "Balance"] = new_balance
    if diff > 0:
        df_fg.at[idx, "In"] = old_in + diff
    df_fg.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df_fg, True, f"✅ تم تعديل رصيد {product_name} من {old_balance:,.0f} إلى {new_balance:,.0f}"

def show_raw_materials(df_raw, t):
    """Display raw materials page"""
    st.header("📦 " + t["raw_materials"])
    
    # التحقق من وجود البيانات
    if df_raw is None:
        st.error("❌ لا توجد بيانات مخزون!")
        st.info(f"الرجاء التأكد من وجود ملف raw.xlsx في المجلد: {BASE_DIR}")
        
        # محاولة إعادة التحميل
        if st.button("🔄 محاولة إعادة تحميل البيانات"):
            st.rerun()
        return
    
    if df_raw.empty:
        st.warning("⚠️ ملف المواد الخام فارغ!")
        return
    
    # عرض إحصائيات
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_items = len(df_raw)
        st.metric("📦 عدد الأصناف", f"{total_items:,}")
    with col2:
        total_stock = df_raw['Current_Stock'].sum() if 'Current_Stock' in df_raw.columns else 0
        st.metric("📊 إجمالي المخزون", f"{total_stock:,.0f}")
    with col3:
        if 'Min_Stock' in df_raw.columns:
            low_stock = len(df_raw[df_raw['Current_Stock'] <= df_raw['Min_Stock']])
            st.metric("⚠️ مواد منخفضة", f"{low_stock:,}")
    with col4:
        if 'Unit_Cost' in df_raw.columns:
            total_value = (df_raw['Current_Stock'] * df_raw['Unit_Cost']).sum()
            st.metric("💰 القيمة الإجمالية", f"{total_value:,.0f}")
    
    st.markdown("---")
    
    # عرض جدول المواد الخام
    st.subheader("📋 قائمة المواد الخام")
    
    # اختيار الأعمدة للعرض
    display_cols = ['Material_ID', 'Material_Name_AR', 'Material_Name_EN', 'Current_Stock', 'Min_Stock', 'Unit']
    available_cols = [col for col in display_cols if col in df_raw.columns]
    
    # تنسيق الأرقام للعرض
    display_df = df_raw[available_cols].copy()
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # قسم تعديل المخزون
    st.markdown("---")
    with st.expander("✏️ " + t["edit_stock"]):
        edit_pw = st.text_input(t["password"], type="password", key="raw_manual_edit_pw")
        if edit_pw in ["admin123", "100"]:
            material = st.selectbox(t["material"], df_raw["Material_Name_AR"], key="raw_manual_material")
            current_qty = float(df_raw.loc[df_raw["Material_Name_AR"] == material, "Current_Stock"].iloc[0])
            st.info(f"الرصيد الحالي: {current_qty:,.0f}")
            new_qty = st.number_input(t["new_stock"], min_value=0, value=int(current_qty), step=1000, key="raw_manual_new_qty")
            if st.button(t["update"], key="raw_manual_update_btn"):
                idx = df_raw[df_raw["Material_Name_AR"] == material].index[0]
                df_raw.at[idx, "Current_Stock"] = new_qty
                if "Last_Updated" in df_raw.columns:
                    df_raw.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d")
                if update_raw_materials(df_raw):
                    st.success(f"{t['stock_updated']}: {material} من {current_qty:,.0f} إلى {new_qty:,.0f}")
                else:
                    st.error("❌ تعذر حفظ التعديل — تأكد أن ملف raw.xlsx غير مفتوح في Excel")
        elif edit_pw:
            st.warning("🔒 كلمة المرور غير صحيحة")
        else:
            st.warning("🔒 يرجى إدخال كلمة مرور المشرف للتعديل")
    
    # قسم استلام مشتريات
    st.markdown("---")
    with st.expander("📥 " + t["receipt"]):
        with st.form("receipt_form"):
            col1, col2 = st.columns(2)
            with col1:
                material = st.selectbox(t["material"], df_raw["Material_Name_AR"])
                qty = st.number_input(t["quantity"], min_value=0, step=1000)
            with col2:
                invoice_no = st.text_input(t["invoice"])
                receipt_date = st.date_input(t["receipt_date"])
            notes = st.text_area("ملاحظات")
            
            if st.form_submit_button(t["register_receipt"], use_container_width=True):
                if qty <= 0:
                    st.error("⚠️ الكمية يجب أن تكون أكبر من صفر")
                else:
                    idx = df_raw[df_raw["Material_Name_AR"] == material].index[0]
                    current = float(df_raw.at[idx, "Current_Stock"])
                    df_raw.at[idx, "Current_Stock"] = current + qty
                    df_raw.at[idx, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d")
                    update_raw_materials(df_raw)
                    
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
                    st.success(f"✅ تم استلام {qty:,.0f} من {material}")

def show_finished_goods(df_fg, t):
    """Display finished goods page"""
    st.header("🏭 " + t["finished_goods"])

    if df_fg is not None and not df_fg.empty:
        df_fg, rolled = apply_monthly_fg_rollover(df_fg.copy())
        if rolled:
            update_finished_goods(df_fg)
            st.success("✅ " + t.get("month_rollover_done", "Monthly balance carried forward"))
    
    if df_fg is None or df_fg.empty:
        st.warning("⚠️ لا توجد بيانات في مخزن الإنتاج التام")
        if st.button("🔄 إنشاء ملف جديد للمنتج التام"):
            new_df = create_sample_finished_goods()
            st.rerun()
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
    
    # عرض الجدول
    st.subheader("📋 قائمة المنتجات التامة")
    display_cols = ['Name', 'Opening_Balance', 'In', 'Out', 'Balance', 'Unit']
    available_cols = [col for col in display_cols if col in df_fg.columns]
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
        with st.form("delivery_form"):
            product = st.selectbox(t["product"], df_fg["Name"])
            current_balance = df_fg[df_fg["Name"] == product]['Balance'].values[0]
            st.info(f"الرصيد الحالي: {current_balance:,.0f}")
            qty = st.number_input(t["quantity_to_deliver"], min_value=0, step=100, max_value=int(current_balance), key="delivery_qty")
            customer = st.text_input(t["customer"])
            notes = st.text_area(t["note_label"])
            
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
                            'notes': notes,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        try:
                            send_telegram(f"🚚 تسليم: {product} - {qty:,.0f} وحدة - {customer}")
                        except:
                            pass
                        st.success(msg)
                    else:
                        st.error(msg)
    
    with tab_manual:
        if st.text_input(t["password"], type="password", key="fg_manual_pw") in ["admin123", "100"]:
            product = st.selectbox(t["product"], df_fg["Name"], key="manual_product")
            current = df_fg[df_fg["Name"] == product]["Balance"].values[0]
            new_balance = st.number_input(t["new_stock"], min_value=0, value=int(current), step=1000, key="manual_balance")
            if st.button(t["update"]):
                new_fg, ok, msg = update_finished_goods_manual_balance(product, new_balance, df_fg)
                if ok:
                    update_finished_goods(new_fg)
                    st.success(msg)
        else:
            st.warning("🔒 يرجى إدخال كلمة مرور المشرف")