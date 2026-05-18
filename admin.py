import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime
from database import load_all_production
from utils import USERS, delete_production_record

def show_users(t):
    """Display users management page"""
    st.header(t["users_title"])
    users_df = pd.DataFrame([{"Username": k, "Name": v["name"], "Role": v["role"]} for k, v in USERS.items()])
    st.dataframe(users_df, use_container_width=True)

def show_settings(t):
    """Display settings page"""
    st.header(t["settings_title"])
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t["backup_data"], use_container_width=True):
            if os.path.exists("smart_factory.db"):
                shutil.copy("smart_factory.db", f"backup_sfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                st.success("Database backup created")
    with col2:
        if st.button(t["clear_cache"], use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared")

def show_delete_records(df_raw, df_fg, t):
    """Display delete records section in sidebar"""
    st.sidebar.divider()
    with st.sidebar.expander("🔒 " + t["admin_title"]):
        pw = st.text_input(t["password"], type="password", key="del_pw")
        if pw in ["admin123", "100"]:
            df_prod = load_all_production()
            if not df_prod.empty:
                if 'id' not in df_prod.columns:
                    st.error("⚠️ ID column not found in database")
                else:
                    df_display = df_prod.copy()
                    df_display['desc'] = df_display.apply(
                        lambda row: f"📦 ID:{row['id']} | {row['date']} | {row['product']} | {row['output_units']} {t['quantity']}", 
                        axis=1
                    )
                    
                    selected_desc = st.selectbox("Select record to delete", options=df_display['desc'].tolist())
                    selected_id = int(selected_desc.split('|')[0].replace('📦 ID:', '').strip())
                    
                    if st.button("🗑️ " + t["delete_btn"], use_container_width=True):
                        ok, msg = delete_production_record(selected_id, df_raw, df_fg)
                        if ok:
                            st.success(f"✅ {msg}")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info("No records to delete")